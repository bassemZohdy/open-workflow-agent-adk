from pathlib import Path

from openworkflow_adk import load_template_catalog


def test_examples_template_catalog_is_complete() -> None:
    catalog = load_template_catalog(Path(__file__).parents[2] / "examples")

    assert {item["name"] for item in catalog} >= {"hello", "approval", "multi-agent"}
