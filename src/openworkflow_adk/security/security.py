"""Runtime security guards for external workflow resources."""

from __future__ import annotations

import ipaddress
import os
from urllib.parse import urlparse


class EgressDeniedError(PermissionError):
    """Raised when a workflow attempts a disallowed network egress."""


def resolve_secret(name: str, environ: dict[str, str] | None = None) -> str | None:
    """Resolve a named secret from deployment environment variables."""
    values = os.environ if environ is None else environ
    return values.get(f"WORKFLOW_SECRET__{name}") or values.get(name)


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


def validate_egress(url: str, environ: dict[str, str] | None = None) -> None:
    """Reject loopback/private/link-local targets unless explicitly allowlisted."""
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
        return
    if address.is_private or address.is_loopback or address.is_link_local or address.is_reserved:
        raise EgressDeniedError(f"egress to {host!r} is blocked")
