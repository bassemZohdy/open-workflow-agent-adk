# open-workflow-agent-adk

Translate OpenWorkflow v1.0.3 YAML/JSON documents into runnable Google ADK
workflows. Tasks can be deterministic nodes or ADK `LlmAgent`s through the
project's task-level `agent` extension.

## Install

```bash
uv sync --extra dev
```

## Run a workflow

```bash
owf-adk run workflow.yaml --input '{"message":"hello"}'
```

The development runtime uses ADK's `InMemorySessionService` and an in-memory
event broker. The library API is asynchronous:

```python
from openworkflow_adk import load, run

events = await run(load("workflow.yaml"), input={"message": "hello"})
```

## Agent task extension

```yaml
do:
  - summarize:
      agent:
        model: gemini-2.5-flash
        instruction: Summarize the input.
      wait:
        seconds: 0
```

See [`docs/extension-spec.md`](docs/extension-spec.md) and the coverage matrix
for supported behavior and intentional limits.

## Development

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```
