"""JSONata evaluation and task mapping helpers."""

from __future__ import annotations

import os
import re
import signal
import threading
from collections.abc import Mapping
from contextlib import contextmanager
from typing import Any

import jsonata


class ExpressionError(ValueError):
    """Raised when an OpenWorkflow expression cannot be evaluated."""


_UNSAFE_FUNCTIONS = ("$eval", "$function")


def _limit(expression: str) -> None:
    if any(token in expression for token in _UNSAFE_FUNCTIONS):
        raise ExpressionError("dynamic expression functions are disabled")
    maximum = int(os.environ.get("WORKFLOW_EXPRESSION_MAX_LENGTH", "10000"))
    if len(expression) > maximum:
        raise ExpressionError(f"expression exceeds maximum length of {maximum}")
    depth = 0
    maximum_depth = 0
    pairs = {"(": ")", "[": "]", "{": "}"}
    for character in expression:
        if character in pairs:
            depth += 1
            maximum_depth = max(maximum_depth, depth)
        elif character in pairs.values():
            depth -= 1
    configured_depth = int(os.environ.get("WORKFLOW_EXPRESSION_MAX_DEPTH", "100"))
    if depth < 0 or maximum_depth > configured_depth:
        raise ExpressionError(f"expression exceeds maximum depth of {configured_depth}")


@contextmanager
def _evaluation_budget() -> Any:
    """Bound synchronous evaluation when running on a POSIX main thread."""
    seconds = float(os.environ.get("WORKFLOW_EXPRESSION_TIMEOUT_SECONDS", "0.25"))
    enabled = os.name == "posix" and threading.current_thread() is threading.main_thread()
    previous = signal.getsignal(signal.SIGALRM) if enabled else None
    if enabled:
        signal.signal(signal.SIGALRM, lambda _signum, _frame: (_ for _ in ()).throw(TimeoutError))
        signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    except TimeoutError as exc:
        raise ExpressionError("expression evaluation exceeded its time budget") from exc
    finally:
        if enabled:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, previous)


def _unwrap(expression: str) -> str:
    expression = expression.strip()
    if expression.startswith("${") and expression.endswith("}"):
        expression = expression[2:-1].strip()
    # OpenWorkflow uses `.` for the current input; JSONata uses `$`.
    expression = "$" + expression if expression.startswith(".") else expression
    # OpenWorkflow examples commonly use JavaScript-style equality; JSONata
    # spells equality with a single equals sign.
    return re.sub(r"(?<![=!])==(?!=)", "=", expression)


def evaluate(expression: Any, data: Mapping[str, Any] | Any = None) -> Any:
    """Evaluate a JSONata expression against workflow data.

    Bare non-string values are returned unchanged. The data mapping may contain
    `context` and `workflow` values; these are also exposed as `$context` and
    `$workflow` through JSONata bindings.
    """
    if not isinstance(expression, str):
        return expression
    expression = _unwrap(expression)
    if not expression:
        return None
    _limit(expression)
    root = data if data is not None else {}
    bindings = {}
    if isinstance(root, Mapping):
        bindings = {
            "context": root.get("context", root.get("$context")),
            "workflow": root.get("workflow", root.get("$workflow")),
        }
    try:
        with _evaluation_budget():
            return jsonata.Jsonata(expression).evaluate(root, bindings)
    except Exception as exc:  # library exposes multiple implementation-specific errors
        raise ExpressionError(f"could not evaluate {expression!r}: {exc}") from exc


def bind(value: Any, data: Mapping[str, Any] | Any = None) -> Any:
    """Recursively evaluate expression-valued strings in a structure."""
    if isinstance(value, str):
        return evaluate(value, data) if value.strip().startswith("${") else value
    if isinstance(value, list):
        return [bind(item, data) for item in value]
    if isinstance(value, dict):
        return {key: bind(item, data) for key, item in value.items()}
    return value


def condition(value: str | None, data: Mapping[str, Any] | Any = None) -> bool:
    """Evaluate an OpenWorkflow condition using JSONata truthiness."""
    if value is None:
        return True
    return bool(evaluate(value, data))


def apply_task_mappings(
    task: Mapping[str, Any], data: Mapping[str, Any], output: Any = None
) -> dict[str, Any]:
    """Apply task `input`, `output`, `export`, and `set` mappings.

    The returned dictionary is a new state mapping. `set` writes named values;
    `export.as` may replace or extend the context using JSONata object output.
    """
    state = dict(data)
    if "set" in task and isinstance(task["set"], Mapping):
        for key, value in task["set"].items():
            state[key] = evaluate(value, state)
    if "output" in task and isinstance(task["output"], Mapping):
        output_as = task["output"].get("as")
        if output_as is not None:
            output = evaluate(output_as, {**state, "output": output})
    if "export" in task and isinstance(task["export"], Mapping):
        export_as = task["export"].get("as")
        if export_as is not None:
            exported = evaluate(export_as, {**state, "output": output})
            if not isinstance(exported, Mapping):
                raise ExpressionError("task export must evaluate to an object")
            state.update(exported)
    return state
