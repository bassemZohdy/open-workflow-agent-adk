"""Derivation of ADK workflow state schemas from workflow inputs and mappings."""

from __future__ import annotations

import re
from typing import Any

from pydantic import ConfigDict, create_model

from openworkflow_adk.models import OpenWorkflowDocument, Task, TaskItem


def _names(value: Any) -> set[str]:
    if isinstance(value, str):
        return set(re.findall(r"(?:\$context|\$workflow|\.)\.?([A-Za-z_][\w-]*)", value))
    if isinstance(value, dict):
        result = set(value)
        for item in value.values():
            result.update(_names(item))
        return result
    if isinstance(value, list):
        result: set[str] = set()
        for item in value:
            result.update(_names(item))
        return result
    return set()


def _task_keys(task: Task) -> set[str]:
    keys: set[str] = set()
    if isinstance(task.set, dict):
        keys.update(task.set)
    if isinstance(task.for_, dict):
        for key in ("each", "at"):
            value = task.for_.get(key)
            if isinstance(value, str):
                keys.add(value)
    if isinstance(task.fork, dict):
        for branch in task.fork.get("branches", []):
            keys.update(_task_keys(TaskItem.model_validate(branch).task))
    catch = getattr(task, "catch", None)
    if isinstance(catch, dict) and isinstance(catch.get("as"), str):
        keys.add(catch["as"])
    for child in [*(task.do or []), *(task.try_ or [])]:
        keys.update(_task_keys(child.task))
    if isinstance(catch, dict):
        for child in catch.get("do", []):
            keys.update(_task_keys(TaskItem.model_validate(child).task))
    keys.update(_names(task.if_))
    keys.update(_names(task.input))
    keys.update(_names(task.output))
    keys.update(_names(task.export))
    return keys


def derive_state_schema(document: OpenWorkflowDocument) -> type:
    """Create an open Pydantic model containing workflow state keys."""
    keys = _names(document.input)
    for item in document.do:
        if item.task.agent is not None:
            keys.add(item.task.agent.output_key or item.name)
        keys.update(_task_keys(item.task))
    for function in document.use.functions.values():
        keys.update(_task_keys(Task.model_validate(function)))
    fields = {key: (Any, None) for key in sorted(keys) if key.isidentifier()}
    return create_model(
        f"{document.document.name.title().replace('-', '')}State",
        __config__=ConfigDict(extra="allow"),
        **fields,
    )
