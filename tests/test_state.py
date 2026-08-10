from openworkflow_adk import load
from openworkflow_adk.state import derive_state_schema


def test_state_schema_contains_input_and_set_keys() -> None:
    document = load(
        {
            "document": {"dsl": "1.0.3", "namespace": "demo", "name": "state", "version": "1.0.0"},
            "input": {"from": ".payload"},
            "do": [{"prepare": {"set": {"status": '"ready"'}}}],
        }
    )

    schema = derive_state_schema(document)
    assert {"payload", "status"} <= set(schema.model_fields)
