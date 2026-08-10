from openworkflow_adk import export_temporal, load


def test_temporal_export_contains_workflow_and_tasks() -> None:
    document = load(
        {
            "document": {
                "dsl": "1.0.3",
                "namespace": "demo",
                "name": "invoice-flow",
                "version": "1.0.0",
            },
            "do": [
                {"fetch": {"set": {"loaded": '"yes"'}}},
                {"notify": {"set": {"sent": '"yes"'}}},
            ],
        }
    )

    source = export_temporal(document)

    assert "class InvoiceFlowWorkflow" in source
    assert "execute_activity" in source
    assert "fetch" in source and "notify" in source
