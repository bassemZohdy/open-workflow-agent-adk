"""Tests for CLI worker and dashboard subcommands."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from openworkflow_adk.cli import main

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


@pytest.fixture
def workflow_dir(tmp_path) -> Path:
    workflow = tmp_path / "wf.yaml"
    workflow.write_text(
        """
document:
  dsl: '1.0.3'
  namespace: demo
  name: polled
  version: '1.0.0'
do:
  - finish:
      set:
        value: '"ok"'
"""
    )
    return tmp_path


def test_cli_worker_start_parses_args(monkeypatch, workflow_dir, postgres_url) -> None:
    import asyncio

    stop_event = asyncio.Event()
    calls = []

    async def fake_run_forever(self) -> None:
        calls.append("run_forever")
        stop_event.set()

    monkeypatch.setattr(
        "openworkflow_adk.ops.polling_worker.PostgresPollingWorker.run_forever", fake_run_forever
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "owf-adk",
            "worker",
            "start",
            "--directory",
            str(workflow_dir),
            "--postgres-url",
            postgres_url,
            "--namespace",
            "cli-worker",
        ],
    )
    main()
    assert calls == ["run_forever"]


def test_cli_dashboard_parses_args(monkeypatch, tmp_path, postgres_url) -> None:
    workflow = tmp_path / "wf.yaml"
    workflow.write_text(
        """
document:
  dsl: '1.0.3'
  namespace: demo
  name: dash
  version: '1.0.0'
do:
  - finish:
      set:
        value: 1
"""
    )
    calls = []

    def fake_serve(*args, **kwargs) -> None:
        calls.append((args, kwargs))

    monkeypatch.setattr("openworkflow_adk.server.serve", fake_serve)
    monkeypatch.setattr(
        "sys.argv",
        [
            "owf-adk",
            "dashboard",
            str(workflow),
            "--postgres-url",
            postgres_url,
            "--namespace",
            "cli-dash",
        ],
    )
    main()
    assert len(calls) == 1
    assert calls[0][1].get("history_config") is not None
