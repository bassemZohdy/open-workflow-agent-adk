"""Builders for nested, error-handling, and looping control flow."""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any

from openworkflow_adk.adk_compat import FunctionNode
from openworkflow_adk.errors import OpenWorkflowError
from openworkflow_adk.expressions import evaluate
from openworkflow_adk.models import Task, TaskItem

from .simple import _dynamic

if TYPE_CHECKING:
    from openworkflow_adk.translator import NodeBuilderRegistry


def _run_nested_builder(
    name: str, children: list[TaskItem], registry: NodeBuilderRegistry
) -> FunctionNode:
    child_nodes = [_dynamic(registry.build(item.name, item.task)) for item in children]

    async def run_nested(ctx: Any, node_input: Any = None) -> Any:
        result = None
        for child in child_nodes:
            result = await ctx.run_node(child, node_input=node_input)
        return result

    return _dynamic(FunctionNode(func=run_nested, name=name))


def _try_builder(name: str, task: Task, registry: NodeBuilderRegistry) -> FunctionNode:
    try_node = _run_nested_builder(name, task.try_ or [], registry)
    _dynamic(try_node)
    catch = task.catch
    catch_children = []
    if isinstance(catch, dict):
        catch_children = [TaskItem.model_validate(item) for item in catch.get("do", [])]
    catch_node = _run_nested_builder(f"{name}__catch", catch_children, registry)
    _dynamic(catch_node)

    async def run_try(ctx: Any) -> Any:
        policy = task.effective_self_heal()
        max_attempts = int(policy.get("max_attempts", 1)) if isinstance(policy, dict) else 1
        for attempt in range(max(1, max_attempts)):
            try:
                return await ctx.run_node(try_node)
            except Exception as error:
                healer = registry.self_healer
                if healer is not None and attempt + 1 < max_attempts:
                    diagnosis = healer(error, ctx.state.to_dict())
                    if inspect.isawaitable(diagnosis):
                        diagnosis = await diagnosis
                    if isinstance(diagnosis, dict) and diagnosis.get("retry"):
                        patch = diagnosis.get("state")
                        if isinstance(patch, dict):
                            ctx.state.update(patch)
                        continue
                if not catch_children:
                    raise
                as_name = catch.get("as") if isinstance(catch, dict) else None
                if as_name:
                    ctx.state[as_name] = OpenWorkflowError.from_exception(error).as_dict()
                return await ctx.run_node(catch_node)

    return _dynamic(FunctionNode(func=run_try, name=name))


def _for_builder(name: str, task: Task, registry: NodeBuilderRegistry) -> FunctionNode:
    children = task.do or []
    child_nodes = [_dynamic(registry.build(item.name, item.task)) for item in children]
    configuration = task.for_ or {}
    each_name = configuration.get("each", "item")
    index_name = configuration.get("at")
    collection_expression = configuration.get("in", "[]")
    while_expression = task.while_

    async def run_for(ctx: Any) -> list[Any]:
        state = ctx.state.to_dict()
        collection = evaluate(collection_expression, state)
        results = []
        for index, item in enumerate(collection or []):
            if while_expression and not evaluate(while_expression, ctx.state.to_dict()):
                break
            ctx.state[each_name] = item
            ctx.session.state[each_name] = item
            if index_name:
                ctx.state[index_name] = index
                ctx.session.state[index_name] = index
            result = None
            for child in child_nodes:
                loop_input = {each_name: item}
                if index_name:
                    loop_input[index_name] = index
                result = await ctx.run_node(child, node_input=loop_input)
            results.append(result)
        return results

    return _dynamic(FunctionNode(func=run_for, name=name))
