from google.adk.agents import LlmAgent

from openworkflow_adk import NodeBuilderRegistry, load


def test_agent_task_builds_single_turn_llm_agent() -> None:
    document = load(
        {
            "document": {"dsl": "1.0.3", "namespace": "demo", "name": "agent", "version": "1.0.0"},
            "do": [
                {
                    "summarize": {
                        "wait": {"seconds": 0},
                        "agent": {"model": "stub-model", "instruction": "Summarize."},
                    }
                }
            ],
        }
    )

    node = NodeBuilderRegistry().build("summarize", document.do[0].task)
    assert isinstance(node, LlmAgent)
    assert node.mode == "single_turn"
    assert node.output_key == "summarize"
