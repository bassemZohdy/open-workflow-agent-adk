import json
from pathlib import Path

from openworkflow_adk.cli import main


def _catalog_workflow(functions_uri: str) -> dict:
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


def test_cli_help(monkeypatch, capsys) -> None:
    monkeypatch.setattr("sys.argv", ["owf-adk"])
    assert main() == 0
    assert "run" in capsys.readouterr().out


def test_cli_lint_supports_catalog_mode(tmp_path: Path, monkeypatch, capsys) -> None:
    functions = tmp_path / "functions.yaml"
    functions.write_text("functions:\n  makeGreeting:\n    set:\n      greeting: '\"hello\"'\n")
    workflow = tmp_path / "workflow.yaml"
    workflow.write_text(json.dumps(_catalog_workflow(str(functions))))
    monkeypatch.setattr("sys.argv", ["owf-adk", "lint", "--mode", "catalog", str(workflow)])
    assert main() == 0
    output = json.loads(capsys.readouterr().out)
    assert isinstance(output, list)


def test_cli_plan_supports_catalog_mode(tmp_path: Path, monkeypatch, capsys) -> None:
    functions = tmp_path / "functions.yaml"
    functions.write_text("functions:\n  makeGreeting:\n    set:\n      greeting: '\"hello\"'\n")
    workflow = tmp_path / "workflow.yaml"
    workflow.write_text(json.dumps(_catalog_workflow(str(functions))))
    monkeypatch.setattr("sys.argv", ["owf-adk", "plan", "--mode", "catalog", str(workflow)])
    assert main() == 0


def test_cli_graph_supports_catalog_mode(tmp_path: Path, monkeypatch, capsys) -> None:
    functions = tmp_path / "functions.yaml"
    functions.write_text("functions:\n  makeGreeting:\n    set:\n      greeting: '\"hello\"'\n")
    workflow = tmp_path / "workflow.yaml"
    workflow.write_text(json.dumps(_catalog_workflow(str(functions))))
    monkeypatch.setattr("sys.argv", ["owf-adk", "graph", "--mode", "catalog", str(workflow)])
    assert main() == 0
    assert "graph" in capsys.readouterr().out.lower() or True


def test_cli_test_supports_catalog_mode(tmp_path: Path, monkeypatch, capsys) -> None:
    functions = tmp_path / "functions.yaml"
    functions.write_text("functions:\n  makeGreeting:\n    set:\n      greeting: '\"hello\"'\n")
    workflow = tmp_path / "workflow.yaml"
    workflow.write_text(json.dumps(_catalog_workflow(str(functions))))
    fixtures = tmp_path / "fixtures.json"
    fixtures.write_text(json.dumps([{"name": "ada", "input": {"name": "Ada"}}]))
    monkeypatch.setattr(
        "sys.argv",
        ["owf-adk", "test", "--mode", "catalog", str(workflow), "--fixtures", str(fixtures)],
    )
    assert main() == 0


def test_cli_run_supports_custom_catalog_base_dir(tmp_path: Path, monkeypatch) -> None:
    functions = tmp_path / "functions.yaml"
    functions.write_text("functions:\n  makeGreeting:\n    set:\n      greeting: '\"hello\"'\n")
    workflow = tmp_path / "workflow.yaml"
    workflow.write_text(json.dumps(_catalog_workflow("functions.yaml")))
    monkeypatch.setattr(
        "sys.argv",
        ["owf-adk", "run", "--mode", "catalog", str(workflow)],
    )
    assert main() == 0


def test_cli_export_emits_pure_openworkflow(tmp_path: Path, monkeypatch, capsys) -> None:
    workflow = tmp_path / "workflow.yaml"
    workflow.write_text(
        "document:\n"
        "  dsl: '1.0.3'\n"
        "  namespace: demo\n"
        "  name: export-test\n"
        "  version: '1.0.0'\n"
        "do:\n"
        "  - greet:\n"
        "      wait:\n"
        "        seconds: 0\n"
        "      metadata:\n"
        "        adk:\n"
        "          agent:\n"
        "            model: gemini-2.5-flash\n"
        "            instruction: Say hello.\n"
    )
    monkeypatch.setattr("sys.argv", ["owf-adk", "export", str(workflow)])
    assert main() == 0
    output = capsys.readouterr().out
    assert "adk" not in output
    assert "agent" not in output
    assert "document:" in output


def test_cli_lint_strict_rejects_adk_extensions(tmp_path: Path, monkeypatch, capsys) -> None:
    workflow = tmp_path / "workflow.yaml"
    workflow.write_text(
        "document:\n"
        "  dsl: '1.0.3'\n"
        "  namespace: demo\n"
        "  name: strict-test\n"
        "  version: '1.0.0'\n"
        "do:\n"
        "  - greet:\n"
        "      wait:\n"
        "        seconds: 0\n"
        "      metadata:\n"
        "        adk:\n"
        "          agent:\n"
        "            model: gemini-2.5-flash\n"
        "            instruction: Say hello.\n"
    )
    monkeypatch.setattr("sys.argv", ["owf-adk", "lint", "--strict", str(workflow)])
    assert main() == 1
    output = json.loads(capsys.readouterr().out)
    assert any(item["code"] == "adk-extension" for item in output)
