import pytest

from openworkflow_adk.security import EgressDeniedError, validate_egress


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
