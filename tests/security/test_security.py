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
