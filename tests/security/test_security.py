from unittest.mock import patch

import socket

import pytest

from openworkflow_adk.security.security import EgressDeniedError, resolve_secret, validate_egress


def test_egress_guard_blocks_private_targets_by_default() -> None:
    with pytest.raises(EgressDeniedError):
        validate_egress("http://127.0.0.1:8080/admin")


def test_egress_guard_allows_explicit_host_allowlist() -> None:
    validate_egress(
        "http://127.0.0.1:8080/admin",
        {"WORKFLOW_EGRESS_ALLOWLIST": "127.0.0.1"},
    )


def test_airgapped_mode_blocks_all_network_egress() -> None:
    with pytest.raises(EgressDeniedError, match="air-gapped"):
        validate_egress("https://example.com", {"WORKFLOW_AIRGAPPED": "1"})


def test_resolve_secret_reads_prefixed_variable() -> None:
    assert resolve_secret("api-key", {"WORKFLOW_SECRET__api-key": "secret"}) == "secret"


def test_resolve_secret_ignores_raw_name_by_default() -> None:
    assert resolve_secret("PATH", {"PATH": "/bin"}) is None


def test_resolve_secret_allows_raw_name_with_opt_in() -> None:
    assert (
        resolve_secret(
            "PATH",
            {"PATH": "/bin", "WORKFLOW_SECRETS_ALLOW_RAW": "1"},
        )
        == "/bin"
    )


def test_egress_guard_skips_dns_resolution_by_default() -> None:
    # Unresolvable hostnames should pass when DNS resolution is not enabled.
    validate_egress("https://definitely-not-a-real-host.invalid")


def test_egress_guard_resolves_dns_when_enabled() -> None:
    with patch(
        "openworkflow_adk.security.security.socket.getaddrinfo",
        return_value=[(None, None, None, None, ("169.254.169.254", 80))],
    ):
        with pytest.raises(EgressDeniedError, match="blocked"):
            validate_egress(
                "https://metadata.example",
                {"WORKFLOW_EGRESS_RESOLVE_DNS": "1"},
            )


def test_egress_guard_blocks_unresolvable_hosts_when_dns_enabled() -> None:
    with patch(
        "openworkflow_adk.security.security.socket.getaddrinfo",
        side_effect=socket.gaierror("Name or service not known"),
    ):
        with pytest.raises(EgressDeniedError, match="could not resolve"):
            validate_egress(
                "https://metadata.example",
                {"WORKFLOW_EGRESS_RESOLVE_DNS": "1"},
            )
