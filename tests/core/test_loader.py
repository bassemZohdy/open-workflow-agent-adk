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
              metadata:
                adk:
                  agent:
                    model: gemini-2.5-flash
                    instruction: Say hello.
        """
    )

    assert document.do[0].name == "waitForIt"
    agent_config = document.do[0].task.effective_agent()
    assert agent_config is not None
    assert agent_config.model == "gemini-2.5-flash"


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
                "do": [
                    {
                        "task": {
                            "wait": {"seconds": 1},
                            "metadata": {"adk": {"agent": {"unknown": True}}},
                        }
                    }
                ],
            }
        )

    assert any("metadata.adk.agent.unknown" in error["path"] for error in raised.value.errors)


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


def test_legacy_agent_task_key_is_rejected_with_migration_hint() -> None:
    with pytest.raises(WorkflowValidationError) as raised:
        load(
            {
                "document": {"dsl": "1.0.3", "namespace": "demo", "name": "x", "version": "1.0.0"},
                "do": [{"task": {"wait": {"seconds": 1}, "agent": {"model": "x"}}}],
            }
        )

    assert any("legacy 'agent'" in error["message"] for error in raised.value.errors)


def test_legacy_use_models_registry_is_rejected_with_migration_hint() -> None:
    with pytest.raises(WorkflowValidationError) as raised:
        load(
            {
                "document": {"dsl": "1.0.3", "namespace": "demo", "name": "x", "version": "1.0.0"},
                "use": {"models": {"fast": {"model": "x"}}},
                "do": [{"finish": {"set": {"value": 1}}}],
            }
        )

    assert any("legacy 'use.models'" in error["message"] for error in raised.value.errors)
