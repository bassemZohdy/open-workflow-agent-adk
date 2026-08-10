import asyncio

import pytest

from openworkflow_adk import SQLiteRunHistory, load, run_workflow


async def test_sqlite_checkpoint_resumes_after_failed_run(tmp_path, monkeypatch) -> None:
    database = tmp_path / "session.db"
    history_path = tmp_path / "history.db"
    monkeypatch.setenv("WORKFLOW_SESSION_DATABASE_URL", f"sqlite+aiosqlite:///{database}")
    document = load(
        {
            "document": {
                "dsl": "1.0.3",
                "namespace": "demo",
                "name": "resume",
                "version": "1.0.0",
            },
            "do": [
                {"prepare": {"set": {"prepared": '"yes"'}}},
                {"work": {"call": "fail"}},
            ],
        }
    )

    def fail() -> None:
        raise RuntimeError("temporary failure")

    history = SQLiteRunHistory(str(history_path))
    with pytest.raises(RuntimeError, match="temporary failure"):
        await asyncio.wait_for(
            run_workflow(
                document,
                session_backend="sqlite",
                session_id="run-1",
                history=history,
                function_registry={"fail": fail},
            ),
            timeout=5,
        )
    history.close()

    restarted_history = SQLiteRunHistory(str(history_path))
    events = await asyncio.wait_for(
        run_workflow(
            document,
            session_backend="sqlite",
            session_id="run-1",
            history=restarted_history,
            function_registry={"fail": lambda: "recovered"},
            resume=True,
        ),
        timeout=5,
    )

    assert events
    assert restarted_history.get("run-1").status == "completed"
    restarted_history.close()
