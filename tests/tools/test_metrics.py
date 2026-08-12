"""Tests for the Prometheus-compatible metrics endpoint."""

from __future__ import annotations

import importlib.util
import os

import pytest

from openworkflow_adk import PostgresRunHistory, load
from openworkflow_adk.ops.postgres_history import PostgresRunHistoryConfig
from openworkflow_adk.server import _prometheus_metrics

pytestmark = [
    pytest.mark.skipif(
        os.environ.get("DOCKER_TESTS") == "0",
        reason="Docker-based tests disabled via DOCKER_TESTS=0",
    ),
]


@pytest.fixture(scope="module")
def postgres_url():
    try:
        from testcontainers.postgres import PostgresContainer  # noqa: PLC0415
    except ImportError as exc:
        pytest.skip(f"testcontainers-postgres not available: {exc}")

    container = PostgresContainer("postgres:16")
    try:
        container.start()
        yield container.get_connection_url().replace("+psycopg2", "").replace("+asyncpg", "")
    except Exception as exc:
        pytest.skip(f"Could not start PostgreSQL container: {exc}")
    finally:
        try:
            container.stop()
        except Exception:
            pass


@pytest.mark.skipif(
    importlib.util.find_spec("fastapi") is None or importlib.util.find_spec("uvicorn") is None,
    reason="server extras not installed",
)
async def test_prometheus_metrics_helper(postgres_url) -> None:
    config = PostgresRunHistoryConfig(url=postgres_url, schema="metrics", namespace_id="ns")
    history = PostgresRunHistory(config)
    await history.connect()
    try:
        await history.start("run-1", "wf", {})
        await history.finish("run-1", state={}, output="done")
        await history.start("run-2", "wf", {})
        await history.finish("run-2", state={}, error=RuntimeError("boom"))

        text = await _prometheus_metrics(history)
        assert 'owf_adk_runs_total{status="completed"} 1' in text
        assert 'owf_adk_runs_total{status="failed"} 1' in text
        assert "owf_adk_run_failures_total 1" in text
        assert "owf_adk_run_duration_seconds" in text
    finally:
        await history.close()


@pytest.mark.skipif(
    importlib.util.find_spec("fastapi") is None or importlib.util.find_spec("uvicorn") is None,
    reason="server extras not installed",
)
def test_metrics_endpoint_without_history() -> None:
    from fastapi.testclient import TestClient

    from openworkflow_adk.server import create_app

    document = load(
        {
            "document": {
                "dsl": "1.0.3",
                "namespace": "demo",
                "name": "metrics",
                "version": "1.0.0",
            },
            "do": [{"finish": {"set": {"value": 1}}}],
        }
    )
    client = TestClient(create_app(document))
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "owf_adk_runs_total" in response.text
