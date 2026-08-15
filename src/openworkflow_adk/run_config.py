"""Frozen configuration object for workflow execution.

``run_workflow`` previously accepted 27 keyword parameters that were re-threaded
through ``build_workflow`` and ``NodeBuilderRegistry``; every new capability
cost four signature edits. Consolidating them into one frozen object means a
capability is added in exactly one place and callers can build and reuse a
config. The keyword form is still accepted for backward compatibility.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from google.genai import types

from openworkflow_adk.registry import WorkflowRegistry
from openworkflow_adk.resources.broker import Broker

if TYPE_CHECKING:
    from google.adk.memory import BaseMemoryService

    from openworkflow_adk.ops.history import InMemoryRunHistory, SQLiteRunHistory
    from openworkflow_adk.ops.logging import JsonRunLogger
    from openworkflow_adk.ops.postgres_history import PostgresRunHistory
    from openworkflow_adk.ops.telemetry import WorkflowTelemetry


@dataclass(frozen=True)
class RunConfig:
    """Immutable settings for a single workflow run."""

    user_id: str = "workflow-user"
    session_id: str = "workflow-session"
    broker: Broker | None = None
    model_factory: Callable[[str], Any] | None = None
    function_registry: dict[str, Callable[..., Any]] | None = None
    session_backend: str | None = None
    workflow_registry: WorkflowRegistry | None = None
    history: InMemoryRunHistory | SQLiteRunHistory | PostgresRunHistory | None = None
    run_logger: JsonRunLogger | Callable[[dict[str, Any]], None] | None = None
    telemetry: WorkflowTelemetry | None = None
    memory_service: BaseMemoryService | None = None
    checkpoint_interval: int | None = None
    resume: bool = False
    suspend_long_waits: bool | None = None
    suspend_after: float | None = None
    resume_input: Any = None
    message: types.Content | None = None
    event_sink: Callable[[Any], None | Awaitable[None]] | None = None
    token_budget: int | None = None
    memoization: Any = None
    self_healer: Callable[[Exception, dict[str, Any]], Any] | None = None
    region: str | None = None
    mode: str = "auto"
    extra: dict[str, Any] = field(default_factory=dict)
