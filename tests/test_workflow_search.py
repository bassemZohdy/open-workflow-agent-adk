from openworkflow_adk import WorkflowRegistry, load


def test_registry_discovers_workflows_by_intent() -> None:
    documents = [
        load(
            {
                "document": {
                    "dsl": "1.0.3",
                    "namespace": "demo",
                    "name": "invoice-alert",
                    "version": "1.0.0",
                    "summary": "Send an invoice payment alert",
                },
                "do": [{"notify": {"set": {"sent": "true"}}}],
            }
        ),
        load(
            {
                "document": {
                    "dsl": "1.0.3",
                    "namespace": "demo",
                    "name": "image-resize",
                    "version": "1.0.0",
                    "summary": "Resize uploaded images",
                },
                "do": [{"resize": {"set": {"done": "true"}}}],
            }
        ),
    ]
    results = WorkflowRegistry(documents).search("invoice payment alert")

    assert results[0].document.document.name == "invoice-alert"
    assert results[0].score == 1.0
