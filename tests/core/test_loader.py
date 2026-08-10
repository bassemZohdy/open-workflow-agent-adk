import pytest

from openworkflow_adk import WorkflowValidationError, load


def test_loads_yaml_task_list_and_agent_extension() -> None:
    document = load(
        """
        document:
          dsl: 1.0.3
          namespace: demo
          name: hello
          version: 1.0.0
        do:
          - waitForIt:
              wait:
                seconds: 1
              agent:
                model: gemini-2.5-flash
                instruction: Say hello.
        """
    )

    assert document.do[0].name == "waitForIt"
    assert document.do[0].task.agent is not None
    assert document.do[0].task.agent.model == "gemini-2.5-flash"


def test_invalid_document_has_structured_path() -> None:
    with pytest.raises(WorkflowValidationError) as raised:
        load({"document": {}, "do": []})

    assert raised.value.errors
    assert any("document" in error["path"] for error in raised.value.errors)


def test_invalid_agent_extension_has_task_path() -> None:
    with pytest.raises(WorkflowValidationError) as raised:
        load(
            {
                "document": {"dsl": "1.0.3", "namespace": "demo", "name": "x", "version": "1.0.0"},
                "do": [{"task": {"wait": {"seconds": 1}, "agent": {"unknown": True}}}],
            }
        )

    assert any("agent.unknown" in error["path"] for error in raised.value.errors)


def test_loader_accepts_additive_patch_dsl_version() -> None:
    document = load(
        {
            "document": {
                "dsl": "1.0.4",
                "namespace": "demo",
                "name": "patch-compatible",
                "version": "1.0.0",
            },
            "do": [{"finish": {"set": {"value": 1}}}],
        }
    )

    assert document.document.dsl == "1.0.4"
