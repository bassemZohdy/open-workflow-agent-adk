"""Runtime security guards for external workflow resources."""

from __future__ import annotations

import ipaddress
import os
import socket
from urllib.parse import urlparse


class EgressDeniedError(PermissionError):
    """Raised when a workflow attempts a disallowed network egress."""


def resolve_secret(name: str, environ: dict[str, str] | None = None) -> str | None:
    """Resolve a named secret from deployment environment variables.

    Secrets are read only from ``WORKFLOW_SECRET__<NAME>`` prefixed variables.
    A fallback to the bare variable name is available only when
    ``WORKFLOW_SECRETS_ALLOW_RAW=1`` is set.
    """
    values = os.environ if environ is None else environ
    prefixed = values.get(f"WORKFLOW_SECRET__{name}")
    if prefixed is not None:
        return prefixed
    if values.get("WORKFLOW_SECRETS_ALLOW_RAW", "").lower() in {"1", "true", "yes"}:
        return values.get(name)
    return None


def redact(value: object, secrets: list[str] | tuple[str, ...] = ()) -> object:
    """Recursively redact known secret values from persisted/logged data."""
    secret_values = [item for item in secrets if item]
    if isinstance(value, str):
        result = value
        for secret in secret_values:
            result = result.replace(secret, "[REDACTED]")
        return result
    if isinstance(value, dict):
        return {key: redact(item, secret_values) for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item, secret_values) for item in value]
    return value


def _block_address(address: ipaddress.IPv4Address | ipaddress.IPv6Address, host: str) -> None:
    if (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_reserved
        or address.is_multicast
    ):
        raise EgressDeniedError(f"egress to {host!r} is blocked")


def validate_egress(url: str, environ: dict[str, str] | None = None) -> None:
    """Reject loopback/private/link-local targets unless explicitly allowlisted.

    By default non-IP hostnames pass through unchanged (the legacy behavior) so
    that deployments without reliable DNS or with mocked hosts keep working. Set
    ``WORKFLOW_EGRESS_RESOLVE_DNS=1`` to resolve every hostname and check all
    resulting addresses; in that mode DNS failures are treated as blocked unless
    ``WORKFLOW_EGRESS_ALLOW_UNRESOLVED=1`` is also set.
    """
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise EgressDeniedError(f"unsupported egress scheme: {parsed.scheme or '<none>'}")
    host = (parsed.hostname or "").lower().rstrip(".")
    values = os.environ if environ is None else environ
    if values.get("WORKFLOW_AIRGAPPED", "").lower() in {"1", "true", "yes"}:
        raise EgressDeniedError("network egress is disabled in air-gapped mode")
    allowlist = {
        item.strip().lower().rstrip(".")
        for item in values.get("WORKFLOW_EGRESS_ALLOWLIST", "").split(",")
        if item.strip()
    }
    if host in allowlist:
        return
    if host in {"localhost", "localhost.localdomain"}:
        raise EgressDeniedError(f"egress to {host!r} is blocked")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        if values.get("WORKFLOW_EGRESS_RESOLVE_DNS", "").lower() not in {"1", "true", "yes"}:
            return
        try:
            infos = socket.getaddrinfo(host, None)
        except socket.gaierror as exc:
            if values.get("WORKFLOW_EGRESS_ALLOW_UNRESOLVED", "").lower() in {"1", "true", "yes"}:
                return
            raise EgressDeniedError(f"could not resolve {host!r} for egress check") from exc
        for info in infos:
            _block_address(ipaddress.ip_address(info[4][0]), host)
        return
    _block_address(address, host)
