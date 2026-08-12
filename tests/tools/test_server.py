"""Tests for the minimal HTTP server."""

from __future__ import annotations

import importlib.util

import pytest

from openworkflow_adk import load


def test_create_app_requires_server_extras(monkeypatch) -> None:
    import sys

    monkeypatch.setitem(sys.modules, "fastapi", None)
    from openworkflow_adk.server import _check_deps

    with pytest.raises(ImportError):
        _check_deps()


@pytest.mark.skipif(
    importlib.util.find_spec("fastapi") is None or importlib.util.find_spec("uvicorn") is None,
    reason="server extras not installed",
)
def test_health_endpoint() -> None:
    from fastapi.testclient import TestClient

    from openworkflow_adk.server import create_app

    document = load(
        {
            "document": {"dsl": "1.0.3", "namespace": "demo", "name": "hello", "version": "1.0.0"},
            "do": [{"finish": {"set": {"value": 1}}}],
        }
    )
    client = TestClient(create_app(document))
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["workflow"] == "hello"


@pytest.mark.skipif(
    importlib.util.find_spec("fastapi") is None or importlib.util.find_spec("uvicorn") is None,
    reason="server extras not installed",
)
def test_run_endpoint_executes_workflow() -> None:
    from fastapi.testclient import TestClient

    from openworkflow_adk.server import create_app

    document = load(
        {
            "document": {"dsl": "1.0.3", "namespace": "demo", "name": "echo", "version": "1.0.0"},
            "do": [{"finish": {"set": {"greeting": '"hello"'}}}],
        }
    )
    client = TestClient(create_app(document))
    response = client.post("/run", json={"input": {"name": "Ada"}})
    assert response.status_code == 200
    data = response.json()
    assert data["workflow"] == "echo"
    assert data["events"]
