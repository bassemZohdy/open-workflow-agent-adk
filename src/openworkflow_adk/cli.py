"""Command-line entrypoint for the OpenWorkflow ADK translator."""

import argparse
import asyncio
import json
import os
from pathlib import Path

from .diagnostics import lint_workflow, workflow_mermaid, workflow_plan
from .diagnostics_server import serve_stdio
from .loader import load
from .runtime import run_workflow


def main() -> int:
    """Run the command-line interface."""
    parser = argparse.ArgumentParser(prog="owf-adk")
    parser.add_argument("--version", action="version", version="%(prog)s 0.1.0")
    commands = parser.add_subparsers(dest="command")
    run_parser = commands.add_parser("run", help="run a workflow document")
    run_parser.add_argument("file", type=Path)
    run_parser.add_argument("--input", default="{}", help="JSON input object")
    run_parser.add_argument("--env", type=Path, help="dotenv-style environment file")
    lint_parser = commands.add_parser("lint", help="lint a workflow document")
    lint_parser.add_argument("file", type=Path)
    plan_parser = commands.add_parser("plan", help="print the compiled workflow plan")
    plan_parser.add_argument("file", type=Path)
    graph_parser = commands.add_parser("graph", help="print the compiled workflow as Mermaid")
    graph_parser.add_argument("file", type=Path)
    test_parser = commands.add_parser("test", help="run workflow cases from fixture JSON")
    test_parser.add_argument("file", type=Path)
    test_parser.add_argument("--fixtures", type=Path, required=True)
    commands.add_parser("diagnostics-server", help="serve editor diagnostics over stdio")
    args = parser.parse_args()
    if args.command == "lint":
        diagnostics = lint_workflow(load(args.file))
        print(json.dumps([item.as_dict() for item in diagnostics], indent=2))
        return 1 if any(item.severity == "error" for item in diagnostics) else 0
    if args.command == "plan":
        print(json.dumps(workflow_plan(load(args.file)), indent=2))
        return 0
    if args.command == "graph":
        print(workflow_mermaid(load(args.file)), end="")
        return 0
    if args.command == "test":
        cases = _load_test_cases(args.fixtures)
        reports = []
        document = load(args.file)
        for index, case in enumerate(cases):
            events = asyncio.run(run_workflow(document, case.get("input", {})))
            outputs = [event.output for event in events if event.output is not None]
            for event in events:
                if event.actions:
                    outputs.extend((event.actions.state_delta or {}).values())
            expected = case.get("output")
            passed = expected is None or expected in outputs
            reports.append({"case": case.get("name", str(index)), "passed": passed})
        print(json.dumps(reports, indent=2))
        return 0 if all(item["passed"] for item in reports) else 1
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
    events = asyncio.run(run_workflow(load(args.file), input_data))
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
