from pathlib import Path

import httpx
import pytest
import respx
from httpx import Response

from openworkflow_adk import CatalogFunctionRegistry, load, run_workflow
from openworkflow_adk.loader import WorkflowValidationError
from openworkflow_adk.resources.catalog import with_catalog_functions


def _workflow(functions_uri: str) -> dict:
    return {
        "document": {
            "dsl": "1.0.3",
            "namespace": "catalog",
            "name": "catalog-workflow",
            "version": "1.0.0",
        },
        "use": {
            "catalogs": {
                "shared": {
                    "endpoint": "https://catalog.example.invalid",
                    "functions": functions_uri,
                }
            }
        },
        "do": [{"greet": {"call": "makeGreeting", "with": {"name": "Ada"}}}],
    }


def test_catalog_functions_load_and_cache(tmp_path: Path) -> None:
    source = tmp_path / "functions.yaml"
    source.write_text("functions:\n  makeGreeting:\n    set:\n      greeting: '\"hello\"'\n")
    registry = CatalogFunctionRegistry()

    first = registry.load(str(source))
    second = registry.load(str(source))

    assert first is second
    assert set(first) == {"makeGreeting"}


def test_catalog_file_uri_and_invalid_function_shape(tmp_path: Path) -> None:
    source = tmp_path / "functions.json"
    source.write_text('{"functions": {"makeGreeting": {"set": {"greeting": "hello"}}}}')

    functions = CatalogFunctionRegistry().load(source.as_uri(), base_dir=tmp_path)

    assert "makeGreeting" in functions
    source.write_text('{"functions": {"broken": "not a task"}}')
    with pytest.raises(ValueError, match="names and tasks"):
        CatalogFunctionRegistry().load(source.as_uri(), base_dir=tmp_path)


def test_catalog_functions_merge_with_workflow_functions(tmp_path: Path) -> None:
    source = tmp_path / "functions.yaml"
    source.write_text("functions:\n  makeGreeting:\n    set:\n      greeting: '\"hello\"'\n")
    document = load(_workflow(str(source)), mode="catalog")

    merged = with_catalog_functions(document, CatalogFunctionRegistry())

    assert "makeGreeting" in merged.use.functions


def test_catalog_function_name_collisions_are_rejected(tmp_path: Path) -> None:
    first = tmp_path / "first.yaml"
    second = tmp_path / "second.yaml"
    first.write_text("functions:\n  same:\n    set:\n      a: '1'\n")
    second.write_text("functions:\n  same:\n    set:\n      b: '2'\n")
    raw = _workflow(str(first))
    raw["use"]["catalogs"]["other"] = {
        "endpoint": "https://catalog.example.invalid",
        "functions": str(second),
    }
    document = load(raw, mode="catalog")

    with pytest.raises(Exception, match="defined by"):
        with_catalog_functions(document, CatalogFunctionRegistry())


@pytest.mark.asyncio
async def test_catalog_function_executes_through_existing_function_path(tmp_path: Path) -> None:
    source = tmp_path / "functions.yaml"
    source.write_text("functions:\n  makeGreeting:\n    set:\n      greeting: '\"hello\"'\n")
    document = load(_workflow(str(source)), mode="catalog")

    events = await run_workflow(document, mode="catalog")

    assert any(
        event.actions and event.actions.state_delta.get("greeting") == "hello" for event in events
    )


@pytest.mark.asyncio
async def test_auto_mode_detects_catalog_and_runs_it(tmp_path: Path) -> None:
    source = tmp_path / "functions.yaml"
    source.write_text("functions:\n  makeGreeting:\n    set:\n      greeting: '\"hello\"'\n")
    document = load(_workflow(str(source)))

    events = await run_workflow(document)

    assert any(
        event.actions and event.actions.state_delta.get("greeting") == "hello" for event in events
    )


@respx.mock
async def test_catalog_llm_wrapping_http_function_produces_output(tmp_path: Path) -> None:
    route = respx.post("https://llm.example.test/chat").mock(
        return_value=Response(200, json={"summary": "short answer"})
    )
    source = tmp_path / "functions.yaml"
    source.write_text(
        "functions:\n"
        "  summarize:\n"
        "    call: http\n"
        "    with:\n"
        "      method: post\n"
        "      endpoint: https://llm.example.test/chat\n"
        "      body:\n"
        "        text: '${ .text }'\n"
    )
    raw = _workflow(str(source))
    raw["do"] = [{"summarize": {"call": "summarize", "with": {"text": "hello"}}}]
    document = load(raw, mode="catalog")

    events = await run_workflow(document, mode="catalog")

    assert route.called
    assert any(event.output == {"summary": "short answer"} for event in events)


def test_catalog_mode_rejects_agent_extension() -> None:
    source = _workflow("functions.yaml")
    source["do"] = [{"agent": {"agent": {"model": "gemini-2.5-flash"}}}]

    with pytest.raises(WorkflowValidationError, match="does not allow"):
        load(source, mode="catalog")


@respx.mock
def test_catalog_http_fetch_does_not_follow_redirects() -> None:
    route = respx.get("https://catalog.example.test/functions.yaml").mock(
        return_value=Response(302, headers={"location": "http://127.0.0.1/private"})
    )

    with pytest.raises(httpx.HTTPStatusError):
        CatalogFunctionRegistry().load("https://catalog.example.test/functions.yaml")
    assert route.called


def test_catalog_file_uri_traversal_is_rejected(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside.yaml"
    outside.write_text("functions: {}")

    with pytest.raises(ValueError, match="escapes"):
        CatalogFunctionRegistry().load(outside.as_uri(), base_dir=tmp_path)


def test_catalog_registry_shares_cached_functions_across_workflows(tmp_path: Path) -> None:
    source = tmp_path / "functions.yaml"
    source.write_text("functions:\n  shared:\n    set:\n      value: '1'\n")
    registry = CatalogFunctionRegistry()

    first = registry.load(source.as_uri(), base_dir=tmp_path)
    second = registry.load(source.as_uri(), base_dir=tmp_path)

    assert first is second
    assert "shared" in second
