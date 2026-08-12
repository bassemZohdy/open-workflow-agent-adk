"""Command-line entrypoint for the OpenWorkflow ADK translator."""

import argparse
import asyncio
import json
import os
from pathlib import Path

from openworkflow_adk.loader import _contains_adk_extension, _to_pure_openworkflow, load, load_raw
from openworkflow_adk.models import OpenWorkflowDocument
from openworkflow_adk.resources.catalog import CatalogFunctionRegistry, with_catalog_functions
from openworkflow_adk.runtime import _has_agent, run_workflow
from openworkflow_adk.tools.diagnostics import (
    Diagnostic,
    lint_workflow,
    workflow_mermaid,
    workflow_plan,
)
from openworkflow_adk.tools.diagnostics_server import serve_stdio


def _add_file_and_mode_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("file", type=Path)
    parser.add_argument("--mode", choices=("auto", "extended", "catalog"), default="auto")
    parser.add_argument(
        "--catalog-base-dir",
        type=Path,
        help="Base directory for resolving relative catalog function URIs",
    )


def _catalog_mode(document: OpenWorkflowDocument, mode: str) -> bool:
    """Mirror load-time and runtime catalog detection."""
    if mode == "catalog":
        return True
    if mode != "auto":
        return False
    return not _has_agent(document.do) and any(
        item.functions for item in document.use.catalogs.values()
    )


def _load_document(args: argparse.Namespace) -> OpenWorkflowDocument:
    document = load(args.file, mode=args.mode)
    base_dir = args.catalog_base_dir or args.file.parent
    if _catalog_mode(document, args.mode):
        document = with_catalog_functions(
            document, CatalogFunctionRegistry(), base_dir=str(base_dir)
        )
    return document


def main() -> int:
    """Run the command-line interface."""
    parser = argparse.ArgumentParser(prog="owf-adk")
    parser.add_argument("--version", action="version", version="%(prog)s 0.2.0")
    commands = parser.add_subparsers(dest="command")

    run_parser = commands.add_parser("run", help="run a workflow document")
    _add_file_and_mode_args(run_parser)
    run_parser.add_argument("--input", default="{}", help="JSON input object")
    run_parser.add_argument("--env", type=Path, help="dotenv-style environment file")

    lint_parser = commands.add_parser("lint", help="lint a workflow document")
    _add_file_and_mode_args(lint_parser)
    lint_parser.add_argument(
        "--strict",
        action="store_true",
        help="also reject ADK extensions so the document is pure OpenWorkflow",
    )

    export_parser = commands.add_parser(
        "export", help="export a workflow document to another format"
    )
    _add_file_and_mode_args(export_parser)
    export_parser.add_argument(
        "--format",
        choices=("openworkflow",),
        default="openworkflow",
        help="output format",
    )
    export_parser.add_argument(
        "--output",
        type=Path,
        help="output file (default: stdout)",
    )

    plan_parser = commands.add_parser("plan", help="print the compiled workflow plan")
    _add_file_and_mode_args(plan_parser)

    graph_parser = commands.add_parser("graph", help="print the compiled workflow as Mermaid")
    _add_file_and_mode_args(graph_parser)

    test_parser = commands.add_parser("test", help="run workflow cases from fixture JSON")
    _add_file_and_mode_args(test_parser)
    test_parser.add_argument("--fixtures", type=Path, required=True)

    serve_parser = commands.add_parser("serve", help="serve a workflow over HTTP")
    _add_file_and_mode_args(serve_parser)
    serve_parser.add_argument("--host", default="127.0.0.1", help="bind host")
    serve_parser.add_argument("--port", type=int, default=8080, help="bind port")

    commands.add_parser("diagnostics-server", help="serve editor diagnostics over stdio")
    args = parser.parse_args()

    if args.command == "lint":
        document = load(args.file, mode=args.mode)
        diagnostics = list(lint_workflow(document))
        if args.strict and _contains_adk_extension(document.model_dump(mode="json")):
            diagnostics.append(
                Diagnostic(
                    "adk-extension",
                    "strict mode: document contains ADK extensions",
                    "$",
                )
            )
        print(json.dumps([item.as_dict() for item in diagnostics], indent=2))
        return 1 if any(item.severity == "error" for item in diagnostics) else 0
    if args.command == "export":
        raw = load_raw(args.file)
        pure = _to_pure_openworkflow(raw)
        import yaml

        output = yaml.safe_dump(pure, sort_keys=False)
        if args.output:
            args.output.write_text(output)
        else:
            print(output, end="")
        return 0
    if args.command == "plan":
        print(json.dumps(workflow_plan(_load_document(args)), indent=2))
        return 0
    if args.command == "graph":
        print(workflow_mermaid(_load_document(args)), end="")
        return 0
    if args.command == "test":
        cases = _load_test_cases(args.fixtures)
        reports = []
        document = load(args.file, mode=args.mode)
        for index, case in enumerate(cases):
            events = asyncio.run(
                run_workflow(
                    document,
                    case.get("input", {}),
                    mode=args.mode,
                    catalog_base_dir=str(args.catalog_base_dir or args.file.parent),
                )
            )
            outputs = [event.output for event in events if event.output is not None]
            for event in events:
                if event.actions:
                    outputs.extend((event.actions.state_delta or {}).values())
            expected = case.get("output")
            passed = expected is None or expected in outputs
            reports.append({"case": case.get("name", str(index)), "passed": passed})
        print(json.dumps(reports, indent=2))
        return 0 if all(item["passed"] for item in reports) else 1
    if args.command == "serve":
        from openworkflow_adk.server import serve as serve_app

        serve_app(
            load(args.file, mode=args.mode),
            host=args.host,
            port=args.port,
        )
        return 0
    if args.command == "diagnostics-server":
        serve_stdio()
        return 0
    if args.command != "run":
        parser.print_help()
        return 0
    if args.env:
        _load_env_file(args.env)
    input_data = json.loads(args.input)
    if not isinstance(input_data, dict):
        parser.error("--input must be a JSON object")
    events = asyncio.run(
        run_workflow(
            load(args.file, mode=args.mode),
            input_data,
            mode=args.mode,
            catalog_base_dir=str(args.catalog_base_dir or args.file.parent),
        )
    )
    for event in events:
        if event.output is not None:
            print(json.dumps(event.output, default=str))
    return 0


def _load_env_file(path: Path) -> None:
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ[key.strip()] = value.strip().strip('"').strip("'")


def _load_test_cases(path: Path) -> list[dict[str, object]]:
    source = path.read_text() if path.is_file() else "[]"
    if path.is_dir():
        cases: list[dict[str, object]] = []
        for fixture in sorted(path.glob("*.json")):
            value = json.loads(fixture.read_text())
            value["name"] = value.get("name", fixture.stem)
            cases.append(value)
        return cases
    value = json.loads(source)
    if isinstance(value, dict):
        return [value]
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError("test fixtures must be a JSON object or array of objects")
    return value
