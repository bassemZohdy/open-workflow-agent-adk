import pytest

from openworkflow_adk import (
    ModelReference,
    ModelSpec,
    build_workflow,
    load,
    resolve_agent_characteristics,
)


def test_named_model_reference_resolves_and_environment_can_repoint_bundle() -> None:
    spec = ModelSpec(model="gemini-fast", generate_content_config={"temperature": 0.1})
    resolved = resolve_agent_characteristics(
        {"model": {"use": "fast"}, "instruction": "task"},
        models={"fast": spec},
        environ={"WORKFLOW_MODELS__FAST__MODEL": "gemini-deployment"},
    )

    assert resolved.model == "gemini-deployment"
    assert resolved.generate_content_config == {"temperature": 0.1}


def test_model_reference_and_literal_model_are_distinct_shapes() -> None:
    assert ModelReference(use="fast").use == "fast"
    assert resolve_agent_characteristics({"model": "fast"}).model == "fast"


def test_unknown_model_reference_is_a_structured_load_error() -> None:
    with pytest.raises(ValueError, match="unknown model reference"):
        load(
            {
                "document": {
                    "dsl": "1.0.3",
                    "namespace": "demo",
                    "name": "unknown-model",
                    "version": "1.0.0",
                },
                "do": [{"agent": {"agent": {"model": {"use": "missing"}}}}],
            }
        )


def test_workflow_agent_uses_named_model_bundle() -> None:
    document = load(
        {
            "document": {
                "dsl": "1.0.3",
                "namespace": "demo",
                "name": "model-bundle",
                "version": "1.0.0",
            },
            "use": {
                "models": {
                    "fast": {
                        "model": "resolved-model",
                        "generate_content_config": {"temperature": 0.2},
                    }
                }
            },
            "do": [
                {
                    "answer": {
                        "wait": {"seconds": 0},
                        "agent": {"model": {"use": "fast"}, "instruction": "Answer."},
                    }
                }
            ],
        }
    )

    workflow = build_workflow(document, model_factory=lambda model: f"factory:{model}")
    agent = workflow.edges[0][1]
    assert agent.model == "factory:resolved-model"
    assert agent.generate_content_config.temperature == 0.2
