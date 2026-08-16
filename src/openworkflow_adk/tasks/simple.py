"""Builders for simple and event-oriented workflow tasks."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any

from openworkflow_adk._utils import response_body
from openworkflow_adk.adk_compat import DEFAULT_ROUTE, FunctionNode
from openworkflow_adk.errors import OpenWorkflowError
from openworkflow_adk.expressions import bind, evaluate
from openworkflow_adk.models import Task
from openworkflow_adk.resources.broker import Broker
from openworkflow_adk.security.auth import resolve_authentication
from openworkflow_adk.security.security import guarded_async_client, validate_egress
from openworkflow_adk.suspension import WorkflowSuspended

from .common import _noop


def _generic_builder(name: str, _task: Task) -> FunctionNode:
    return FunctionNode(func=_noop, name=name)


def _wait_builder(
    name: str, task: Task, *, suspend_long_waits: bool = False, suspend_after: float = 3600
) -> FunctionNode:
    async def wait(ctx: Any) -> None:
        if isinstance(task.wait, dict):
            seconds = float(task.wait.get("seconds", 0))
            seconds += float(task.wait.get("minutes", 0)) * 60
            seconds += float(task.wait.get("hours", 0)) * 3600
            seconds += float(task.wait.get("milliseconds", 0)) / 1000
            if suspend_long_waits and seconds >= suspend_after:
                raise WorkflowSuspended(
                    task=name,
                    resume_at=datetime.now(timezone.utc) + timedelta(seconds=seconds),
                )
            await asyncio.sleep(seconds)

    return FunctionNode(func=wait, name=name)


def _raise_builder(name: str, task: Task) -> FunctionNode:
    async def raise_error(ctx: Any) -> None:
        error = (task.raise_ or {}).get("error", task.raise_ or {})
        if not isinstance(error, dict):
            error = {"detail": str(error)}
        raise OpenWorkflowError(
            type=str(error.get("type", "about:blank")),
            status=error.get("status"),
            title=error.get("title"),
            detail=error.get("detail"),
            instance=error.get("instance"),
        )

    return FunctionNode(func=raise_error, name=name)


def _http_builder(
    name: str,
    task: Task,
    policies: dict[str, Any] | None = None,
    environ: dict[str, str] | None = None,
) -> FunctionNode:
    async def request(ctx: Any) -> Any:
        state = ctx.state.to_dict()
        arguments = bind(task.with_ or {}, state)
        endpoint = arguments.get("endpoint")
        endpoint_auth = endpoint.get("authentication") if isinstance(endpoint, dict) else None
        if isinstance(endpoint, dict):
            endpoint = endpoint.get("uri")
        if not endpoint:
            raise ValueError(f"HTTP task {name!r} requires with.endpoint")
        validate_egress(endpoint, environ)
        method = str(arguments.get("method", "get")).upper()
        output = arguments.get("output", "content")
        follow_redirects = bool(arguments.get("redirect", False))
        auth, auth_headers = resolve_authentication(endpoint_auth, policies, environ)
        headers = dict(arguments.get("headers") or {})
        headers.update(auth_headers)
        async with guarded_async_client(environ, follow_redirects=follow_redirects) as client:
            response = await client.request(
                method,
                endpoint,
                headers=headers,
                params=arguments.get("query"),
                json=arguments.get("body"),
                auth=auth,
            )
            if 300 <= response.status_code < 400 and not follow_redirects:
                response.raise_for_status()
            response.raise_for_status()
            if output == "raw":
                return response.content
            if output == "response":
                return {
                    "status": response.status_code,
                    "headers": dict(response.headers),
                    "body": response_body(response),
                }
            return response_body(response)

    return FunctionNode(func=request, name=name)


def _set_builder(name: str, task: Task) -> FunctionNode:
    async def set_values(ctx: Any, node_input: Any = None) -> None:
        if isinstance(task.set, dict):
            state = ctx.state.to_dict()
            if isinstance(node_input, dict):
                state.update(node_input)
            for key, value in task.set.items():
                ctx.state[key] = evaluate(value, state)
                state[key] = ctx.state[key]

    return FunctionNode(func=set_values, name=name)


def _emit_builder(name: str, task: Task, broker: Broker | None) -> FunctionNode:
    async def emit(ctx: Any) -> None:
        if broker is None:
            return
        event = ((task.emit or {}).get("event") or {}).get("with", {})
        await broker.publish(bind(event, ctx.state.to_dict()))

    return FunctionNode(func=emit, name=name)


def _listen_builder(
    name: str, task: Task, broker: Broker | None, *, suspend_listens: bool = False
) -> FunctionNode:
    async def listen(ctx: Any) -> Any:
        if broker is None:
            return None
        configuration = (task.listen or {}).get("to", {})
        read_mode = (task.listen or {}).get("read", "data")
        filters: list[dict[str, Any]] = []
        strategy = "one"
        if isinstance(configuration, dict):
            if "one" in configuration:
                filters = [configuration["one"]]
            elif "any" in configuration:
                strategy, filters = "any", configuration["any"]
            elif "all" in configuration:
                strategy, filters = "all", configuration["all"]
        types_to_match = {
            (item.get("with") or {}).get("type") for item in filters if isinstance(item, dict)
        }
        if suspend_listens:
            raise WorkflowSuspended(
                task=name,
                resume_at=datetime.now(timezone.utc),
                reason="broker_listen",
            )

        async def next_event() -> dict[str, Any]:
            while True:
                event = await broker.consume()
                if not types_to_match or event.get("type") in types_to_match:
                    return event

        if strategy == "all":
            events = [await next_event() for _ in filters]
            result: Any = events
        else:
            result = await next_event()
        if read_mode == "data":
            if isinstance(result, list):
                return [event.get("data") for event in result]
            return result.get("data")
        return result

    return FunctionNode(func=listen, name=name)


def _switch_builder(name: str, task: Task) -> FunctionNode:
    async def route(ctx: Any) -> None:
        state = ctx.state.to_dict()
        default = DEFAULT_ROUTE
        for case in task.switch or []:
            if not isinstance(case, dict):
                continue
            case_name, configuration = next(iter(case.items()))
            if case_name == "default":
                default = case_name
            elif isinstance(configuration, dict) and evaluate(configuration.get("when"), state):
                ctx.route = case_name
                return
        ctx.route = default

    return FunctionNode(func=route, name=name)


def _compete_builder(name: str, branches: list[Any]) -> FunctionNode:
    async def compete(ctx: Any) -> Any:
        tasks = {
            asyncio.create_task(ctx.run_node(branch, use_sub_branch=True)) for branch in branches
        }
        if not tasks:
            return None
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for pending_task in pending:
            pending_task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
        winner = next(iter(done))
        return winner.result()

    return _dynamic(FunctionNode(func=compete, name=name))


def _dynamic(node: Any) -> Any:
    """Mark a node safe for ADK dynamic execution via ``ctx.run_node``."""
    if hasattr(node, "rerun_on_resume"):
        node.rerun_on_resume = True
    return node
