from openworkflow_adk import load, memory_service_for_document
from openworkflow_adk.resources.memory import InMemoryMemoryService


def test_memory_service_discovered_from_nested_agent() -> None:
    document = load(
        {
            "document": {
                "dsl": "1.0.3",
                "namespace": "demo",
                "name": "nested-memory",
                "version": "1.0.0",
                "metadata": {
                    "adk": {
                        "memories": {"short": {"type": "in-memory"}},
                    }
                },
            },
            "do": [
                {
                    "outer": {
                        "do": [
                            {
                                "inner": {
                                    "wait": {"seconds": 0},
                                    "metadata": {
                                        "adk": {
                                            "agent": {
                                                "model": "gemini-2.5-flash",
                                                "instruction": "hi",
                                                "memory": {"use": "short"},
                                            }
                                        }
                                    },
                                }
                            }
                        ]
                    }
                }
            ],
        }
    )

    service = memory_service_for_document(document)

    assert isinstance(service, InMemoryMemoryService)
