from pathlib import Path
from time import monotonic

import pytest

from openworkflow_adk.expressions import ExpressionError, evaluate

HOSTILE_EXPRESSIONS = [
    line.strip()
    for line in (Path(__file__).parents[2] / "tests" / "data" / "hostile_expressions.txt")
    .read_text()
    .splitlines()
    if line.strip() and not line.lstrip().startswith("#")
]


def test_expression_length_and_depth_are_bounded(monkeypatch) -> None:
    monkeypatch.setenv("WORKFLOW_EXPRESSION_MAX_LENGTH", "8")
    with pytest.raises(ExpressionError, match="maximum length"):
        evaluate("123456789")

    monkeypatch.setenv("WORKFLOW_EXPRESSION_MAX_LENGTH", "1000")
    monkeypatch.setenv("WORKFLOW_EXPRESSION_MAX_DEPTH", "2")
    with pytest.raises(ExpressionError, match="maximum depth"):
        evaluate("(((1)))")

    with pytest.raises(ExpressionError, match="dynamic expression"):
        evaluate('$eval("1+1")')


@pytest.mark.parametrize("expression", HOSTILE_EXPRESSIONS)
def test_hostile_expression_corpus_is_bounded(monkeypatch, expression: str) -> None:
    monkeypatch.setenv("WORKFLOW_EXPRESSION_MAX_LENGTH", "256")
    monkeypatch.setenv("WORKFLOW_EXPRESSION_MAX_DEPTH", "16")
    monkeypatch.setenv("WORKFLOW_EXPRESSION_TIMEOUT_SECONDS", "0.05")
    started = monotonic()
    try:
        evaluate(expression)
    except ExpressionError:
        pass
    assert monotonic() - started < 1
