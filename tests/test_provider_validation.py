import pytest

from openworkflow_adk import load
from openworkflow_adk.loader import WorkflowValidationError


def test_unknown_model_provider_reference_is_structured() -> None:
    with pytest.raises(WorkflowValidationError, match="unknown provider reference"):
        load(
            {
                "document": {
                    "dsl": "1.0.3",
                    "namespace": "demo",
                    "name": "bad-provider",
                    "version": "1.0.0",
                },
                "use": {"models": {"model": {"model": "gpt", "provider": {"use": "missing"}}}},
                "do": [
                    {
                        "answer": {
                            "wait": {"seconds": 0},
                            "agent": {"model": {"use": "model"}, "instruction": "x"},
                        }
                    }
                ],
            }
        )
