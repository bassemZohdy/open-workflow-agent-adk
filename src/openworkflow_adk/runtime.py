"""Development runtime helpers for assembled ADK workflows."""

from __future__ import annotations

import os
import time
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any

from google.adk.memory import BaseMemoryService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from openworkflow_adk.models import OpenWorkflowDocument
from openworkflow_adk.ops import replay as _replay
from openworkflow_adk.ops.history import InMemoryRunHistory, SQLiteRunHistory
from openworkflow_adk.ops.logging import JsonRunLogger
from openworkflow_adk.ops.schedule import trigger_events
from openworkflow_adk.ops.suspension import WorkflowSuspended
from openworkflow_adk.ops.telemetry import WorkflowTelemetry
from openworkflow_adk.resources.broker import Broker, InMemoryBroker
from openworkflow_adk.resources.catalog import CatalogFunctionRegistry, with_catalog_functions
from openworkflow_adk.resources.memory import create_memory_service
from openworkflow_adk.security.security import redact, resolve_secret
from openworkflow_adk.tools.registry import WorkflowRegistry
from openworkflow_adk.translator import build_workflow

replay_event_log = _replay.replay_event_log


def _has_agent(items: list[Any]) -> bool:
    """Recursively check whether any task uses the agent extension."""
    from openworkflow_adk.models import TaskItem

    for item in items:
        if isinstance(item, dict):
            item = TaskItem.model_validate(item)
        if item.task.agent is not None:
            return True
        if item.task.do and _has_agent(item.task.do):
            return True
        if item.task.try_ and _has_agent(item.task.try_):
            return True
        fork = item.task.fork or {}
        if isinstance(fork, dict) and _has_agent(fork.get("branches", [])):
            return True
        for case in item.task.switch or []:
            if isinstance(case, dict):
                configuration = next(iter(case.values())) if case else {}
                if isinstance(configuration, dict) and _has_agent(configuration.get("do", [])):
                    return True
    return False


replay_from_task = _replay.replay_from_task
verify_replay_determinism = _replay.verify_replay_determinism


async def run_workflow(
    document: OpenWorkflowDocument,
    input: dict[str, Any] | None = None,
    *,
    user_id: str = "workflow-user",
    session_id: str = "workflow-session",
    broker: Broker | None = None,
    model_factory: Callable[[str], Any] | None = None,
    function_registry: dict[str, Callable[..., Any]] | None = None,
    session_backend: str | None = None,
    workflow_registry: WorkflowRegistry | None = None,
    history: InMemoryRunHistory | SQLiteRunHistory | None = None,
    run_logger: JsonRunLogger | Callable[[dict[str, Any]], None] | None = None,
    telemetry: WorkflowTelemetry | None = None,
    memory_service: BaseMemoryService | None = None,
    checkpoint_interval: int | None = None,
    resume: bool = False,
    suspend_long_waits: bool | None = None,
    suspend_after: float | None = None,
    resume_input: Any = None,
    message: types.Content | None = None,
    event_sink: Callable[[Any], None | Awaitable[None]] | None = None,
    token_budget: int | None = None,
    memoization: Any = None,
    self_healer: Callable[[Exception, dict[str, Any]], Any] | None = None,
    region: str | None = None,
    mode: str = "auto",
    catalog_registry: CatalogFunctionRegistry | None = None,
    catalog_base_dir: str | None = None,
) -> list[Any]:
    """Run a translated workflow using the selected ADK session backend."""
    if resume and history is None:
        raise ValueError("resume requires a persistent run history")
    if resume and history is not None:
        try:
            prior = history.get(session_id)
        except KeyError:
            prior = None
        if prior is not None and prior.checkpoint_task:
            if region is not None and prior.region is not None and prior.region != region:
                raise RuntimeError(
                    f"run region {prior.region!r} does not match requested region {region!r}"
                )
            if prior.status == "suspended" and prior.resume_at:
                resume_at = datetime.fromisoformat(prior.resume_at)
                if resume_at > datetime.now(timezone.utc):
                    raise RuntimeError(
                        f"workflow timer has not elapsed; resume_at={prior.resume_at}"
                    )
            start_at_checkpoint = prior.suspension_reason not in {"human_input", "broker_listen"}
            for index, item in enumerate(document.do):
                if item.name == prior.checkpoint_task:
                    if start_at_checkpoint:
                        document = document.model_copy(update={"do": document.do[index + 1 :]})
                    input = prior.state
                    break
            else:
                raise KeyError(f"checkpoint task {prior.checkpoint_task!r} is not in workflow")
    if mode not in {"auto", "extended", "catalog"}:
        raise ValueError("mode must be auto, extended, or catalog")
    has_agent = _has_agent(document.do)
    if mode == "catalog" and has_agent:
        raise ValueError("catalog mode does not allow the agent extension")
    catalog_mode = mode == "catalog" or (
        mode == "auto"
        and not has_agent
        and any(item.functions for item in document.use.catalogs.values())
    )
    if catalog_mode:
        document = with_catalog_functions(
            document,
            catalog_registry or CatalogFunctionRegistry(),
            base_dir=catalog_base_dir,
        )
    workflow = build_workflow(
        document,
        broker=broker or InMemoryBroker(),
        model_factory=model_factory,
        function_registry=function_registry,
        workflow_registry=workflow_registry,
        suspend_long_waits=history is not None
        if suspend_long_waits is None
        else suspend_long_waits,
        suspend_after=(
            float(os.environ.get("WORKFLOW_SUSPEND_WAIT_SECONDS", "3600"))
            if suspend_after is None
            else suspend_after
        ),
        resume_input=resume_input,
        suspend_listens=history is not None and not resume,
        memoization=memoization,
        self_healer=self_healer,
    )
    if history is not None and not resume:
        history.start(session_id, document.document.name, input or {}, region=region)
    secret_values = [
        value for name in document.use.secrets if (value := resolve_secret(name)) is not None
    ]
    if run_logger:
        run_logger(
            {
                "event": "run.started",
                "run_id": session_id,
                "workflow": document.document.name,
            }
        )
        for task in document.do:
            run_logger({"event": "task.enter", "run_id": session_id, "task": task.name})
    backend = session_backend or os.environ.get("WORKFLOW_SESSION_BACKEND", "inmemory")
    if backend == "inmemory":
        sessions = InMemorySessionService()
    elif backend in {"database", "sqlite"}:
        from google.adk.sessions.database_session_service import DatabaseSessionService

        database_url = os.environ.get(
            "WORKFLOW_SESSION_DATABASE_URL", "sqlite+aiosqlite:///workflow-sessions.db"
        )
        sessions = DatabaseSessionService(db_url=database_url)
    elif backend == "vertex":
        from google.adk.sessions.vertex_ai_session_service import VertexAiSessionService

        sessions = VertexAiSessionService(
            project=os.environ.get("GOOGLE_CLOUD_PROJECT"),
            location=os.environ.get("GOOGLE_CLOUD_LOCATION"),
            agent_engine_id=os.environ.get("WORKFLOW_VERTEX_AGENT_ENGINE_ID"),
        )
    else:
        raise ValueError(f"unsupported session backend: {backend!r}")
    existing = await sessions.get_session(
        app_name=document.document.name,
        user_id=user_id,
        session_id=session_id,
    )
    if existing is None:
        await sessions.create_session(
            app_name=document.document.name,
            user_id=user_id,
            session_id=session_id,
            state=input or {},
        )
    active_memory_service = memory_service or memory_service_for_document(document)
    runner = Runner(
        node=workflow,
        app_name=document.document.name,
        session_service=sessions,
        memory_service=active_memory_service,
    )
    message = message or types.Content(
        role="user",
        parts=[types.Part(text="Run workflow")],
    )
    try:
        started = time.monotonic()
        events: list[Any] = []
        state = dict(input or {})
        interval = checkpoint_interval
        if interval is None:
            interval = int(os.environ.get("WORKFLOW_CHECKPOINT_INTERVAL", "1"))
        if interval < 0:
            raise ValueError("checkpoint_interval must be non-negative")
        if token_budget is not None and token_budget < 0:
            raise ValueError("token_budget must be non-negative")
        consumed_tokens = 0
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=message,
        ):
            events.append(event)
            consumed_tokens += _event_token_count(event)
            if token_budget is not None and consumed_tokens > token_budget:
                raise RuntimeError(
                    f"workflow token budget exceeded: {consumed_tokens}>{token_budget}"
                )
            if event_sink is not None:
                delivered = event_sink(event)
                if hasattr(delivered, "__await__"):
                    await delivered
            if event.actions:
                state.update(event.actions.state_delta or {})
            if history is not None:
                history.record_event(session_id, _event_log_entry(event))
            if (
                history is not None
                and interval
                and len(events) % interval == 0
                and not event.error_code
                and not event.error_message
            ):
                history.checkpoint(
                    session_id,
                    state=redact(state, secret_values),
                    index=len(events),
                    task=_event_task_name(event),
                )
        if active_memory_service is not None:
            session = await sessions.get_session(
                app_name=document.document.name,
                user_id=user_id,
                session_id=session_id,
            )
            if session is not None:
                await active_memory_service.add_session_to_memory(session)
    except WorkflowSuspended as suspension:
        if history is None:
            raise
        history.suspend(
            session_id,
            state=redact(state, secret_values),
            index=len(events),
            task=suspension.task,
            resume_at=suspension.resume_at.isoformat(),
            reason=suspension.reason,
        )
        if run_logger:
            run_logger(
                {
                    "event": "run.suspended",
                    "run_id": session_id,
                    "task": suspension.task,
                    "resume_at": suspension.resume_at.isoformat(),
                }
            )
        return events
    except Exception as error:
        safe_error = RuntimeError(str(redact(str(error), secret_values)))
        if history is not None:
            history.finish(session_id, state=redact(state, secret_values), error=safe_error)
        if run_logger:
            run_logger(
                {
                    "event": "run.failed",
                    "run_id": session_id,
                    "error": str(safe_error),
                    "duration_ms": round((time.monotonic() - started) * 1000, 3),
                }
            )
        raise
    if history is not None:
        history.finish(
            session_id,
            state=redact(state, secret_values),
            output=redact(events[-1].output if events else None, secret_values),
        )
    if run_logger:
        for event in events:
            run_logger(
                {
                    "event": "task.exit",
                    "run_id": session_id,
                    "task": event.author,
                    "output": redact(event.output, secret_values),
                    "state_delta": redact(
                        event.actions.state_delta if event.actions else {}, secret_values
                    ),
                    "duration_ms": round((time.monotonic() - started) * 1000, 3),
                    "route": getattr(event.actions, "escalate", None) if event.actions else None,
                }
            )
        run_logger(
            {
                "event": "run.completed",
                "run_id": session_id,
                "workflow": document.document.name,
                "duration_ms": round((time.monotonic() - started) * 1000, 3),
            }
        )
    if telemetry:
        telemetry.record_run(document.document.name, session_id, events)
    return events


def _event_task_name(event: Any) -> str | None:
    node_info = getattr(event, "node_info", None)
    path = getattr(node_info, "path", None) if node_info else None
    if not path:
        return None
    return str(path).rsplit("/", 1)[-1].split("@", 1)[0]


def _event_token_count(event: Any) -> int:
    """Read ADK usage metadata without requiring a specific event version."""
    usage = getattr(event, "usage_metadata", None)
    if usage is None:
        return 0
    return int(getattr(usage, "total_token_count", 0) or 0)


def _event_log_entry(event: Any) -> dict[str, Any]:
    return {
        "task": _event_task_name(event),
        "output": event.output,
        "state_delta": event.actions.state_delta if event.actions else {},
        "error": event.error_message or event.error_code,
    }


async def run(document: OpenWorkflowDocument, input: dict[str, Any] | None = None) -> list[Any]:
    """Public library entrypoint for an in-memory workflow run."""
    return await run_workflow(document, input)


def memory_service_for_document(document: OpenWorkflowDocument) -> BaseMemoryService | None:
    """Build the first referenced memory backend for a workflow host.

    ADK's Runner exposes one memory service per run. Workflows that need
    multiple stores should use separate hosts until a routing memory service
    is introduced.
    """
    for item in document.do:
        if item.task.agent and item.task.agent.memory:
            reference = item.task.agent.memory.use
            config = document.use.memories.get(reference)
            if config is None:
                raise ValueError(f"unknown memory reference {reference!r}")
            return create_memory_service(config)
    return None


async def run_scheduled(
    document: OpenWorkflowDocument,
    input: dict[str, Any] | None = None,
    *,
    broker: Broker | None = None,
    max_runs: int | None = None,
) -> list[list[Any]]:
    """Run a scheduled workflow, optionally stopping after ``max_runs`` triggers."""
    results: list[list[Any]] = []
    async for _ in trigger_events(document, broker):
        results.append(await run_workflow(document, input, broker=broker))
        if max_runs is not None and len(results) >= max_runs:
            break
    return results
