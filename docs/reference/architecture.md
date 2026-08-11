# Architecture

Detailed translation reference for `open-workflow-agent-adk`. [`CLAUDE.md`](../CLAUDE.md) holds the
concise baseline (project, config precedence, stack); this doc expands the pipeline, the task→ADK
mapping, and the ADK gotchas implementers must honor. Task status lives in [`TODO.md`](../TODO.md).

## Pipeline

```
workflow.yaml/json
   │  1. load (PyYAML / json)
   ▼
OpenWorkflowDocument (typed pydantic model)
   │  2. validate ADK payload (`metadata.adk`) with Pydantic
   │  3. strip legacy direct ADK properties and validate against vendored 1.0.3 schema
   │  4. resolve config (env > per-task `metadata.adk.agent` > legacy `agent:` > project defaults)
   ▼
Resolved tasks + agent characteristics
   │  5. translate: each task → ADK node (LlmAgent | FunctionNode | nested Workflow)
   │                  taskList `do` → edge chain; `then`/`switch`/`fork` → edges/routes
   │                  JSONata expressions (${…}) → expression evaluator over ctx.state
   ▼
adk.Workflow(edges=…, state_schema=…)
   │  6. run via adk.Runner + InMemorySessionService (dev) / Vertex (prod)
   ▼
events / output
```

**Core extension**: a task carrying agent-characteristics config (model/instructions/tools) compiles
to an `adk.Agent` node; a task without it compiles to a deterministic `FunctionNode`. Tasks without
agent config fall back to project-wide defaults (3-layer precedence — see
[`configuration.md`](configuration.md)).

## Key mapping (OpenWorkflow task → ADK construct)

| OpenWorkflow | ADK |
|---|---|
| `do` taskList | sequential edge chain `("START", t1, t2, …)` |
| `then: continue` | implicit edge to next task |
| `then: end`/`exit` | terminal node (no out-edge) |
| `then: <namedTask>` | explicit edge to that named task (goto) |
| `switch` | router `FunctionNode` yields `Event(route=case)` + `RoutingMap` edge; default → `DEFAULT_ROUTE` |
| `fork` (no compete) | fan-out `(joinPoint, (branchA, branchB))` → `JoinNode` fan-in |
| `fork.compete: true` | race: custom coordinator node, first completion wins, cancel siblings |
| `try`/`catch` | wrapper `FunctionNode` runs try-tasks via `ctx.run_node`, catches, runs catch-tasks; `retry` → `RetryConfig` |
| `for` (+`while`) | loop `FunctionNode`: iterate collection, dispatch `do` per item via `ctx.run_node` |
| `wait` (duration) | `FunctionNode` → `asyncio.sleep(duration)` |
| `set` | `FunctionNode` writes `ctx.state` (state_delta) |
| `raise` | `FunctionNode` raises typed error (caught by enclosing `try`) |
| `emit`/`listen` | broker-adapter interface (pluggable); emit publishes, listen awaits |
| `call: http` | `FunctionNode` + httpx |
| `call: grpc`/`openapi`/`asyncapi` | `FunctionNode` + protocol client |
| `call: a2a`/`mcp` | reuse ADK a2a/mcp tooling |
| `call: function` (named) | lookup in `use.functions` registry → `FunctionNode` |
| `run: shell`/`script`/`container`/`workflow` | subprocess / code-exec / docker SDK / nested Workflow |
| `if` (taskBase) | guard: skip node if expression false (conditional edge or in-node check) |
| `input`/`output`/`export` | node_input shaping + `output_key` + `$context` write (JSONata) |
| taskBase `timeout` | `FunctionNode(timeout=…)` / `RetryConfig` |
| `use.retries` | `RetryConfig` references |
| `use.authentications` | `AuthConfig` on nodes |
| **task with `metadata.adk.agent`** | `adk.Agent`(model, instruction, tools, output_schema, output_key); legacy `agent:` is also accepted |
| `document.metadata.adk.models` / `use.models` (extension) | named `ModelSpec` registry; agent `model: {use: name}` resolves a model + generation-config bundle. `document.metadata.adk.models` takes precedence |
| `document.metadata.adk.providers` / `use.providers` (extension) | named `ProviderConfig` registry; a model references one; resolved to an ADK `BaseLlm` via the provider factory. `document.metadata.adk.providers` takes precedence |
| `document.metadata.adk.memories` / `use.memories` (extension) | named `MemoryConfig` registry; agent `memory: {use: name}` resolves to an ADK `BaseMemoryService`. `document.metadata.adk.memories` takes precedence |

The broker interface also ships CloudEvents 1.0 adapters for Redis Streams,
Kafka, RabbitMQ, and NATS. Their client SDKs are lazy and available through
the optional `brokers` extra; tests can inject a transport client directly.

## ADK gotchas to honor

- `mode='task'` `LlmAgent`s **cannot** be static graph nodes (validated against in `_workflow.py`).
  Task-mode agents must be chat sub-agents or dispatched via `ctx.run_node`. Default agent-tasks to
  `single_turn` when used as graph nodes.
- A workflow allows **exactly one** terminal output; multiple terminal-node outputs raise. `fork`
  without join and multiple `then: end` branches must funnel through a `JoinNode`.
- `state_schema` (pydantic BaseModel) declares workflow state; every `FunctionNode` param (except
  `ctx`/`node_input`/`self`) must be a field on it (validated at build time).
- `output_key` on an `Agent` persists its reply into `ctx.state` — maps to taskBase `output`.
- OpenWorkflow expressions are **JSONata** (`${ .x }`, `$workflow.…`); ADK instruction placeholders
  are `{var}` from state. Two different mechanisms — bridge, don't conflate.
