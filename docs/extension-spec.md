# Agent-characteristics extension

This project extends OpenWorkflow v1.0.3 with an optional `agent` object on any
task. The upstream schema remains authoritative for every other task property.

```yaml
agent:
  model: gemini-2.5-flash
  instruction: Answer using the supplied context.
  tools: []
  agent: true
  generate_content_config: {}
  output_key: answer
  request_input:
    question: Approve this action?
```

`agent` omitted, or `agent: false`, produces a deterministic ADK node. When the
extension is enabled, the translator creates an `LlmAgent` with `mode:
single_turn` and persists its result under `output_key` (default: task name).

Configuration is resolved in this order:

1. `WORKFLOW_` environment variables
2. task-level `agent` values
3. project defaults

The validator strips only `agent` before applying the vendored upstream JSON
Schema, then validates the extension with Pydantic. This makes the divergence
explicit and keeps upstream validation strict.

`use.providers` and `use.memories` are additional registries. A model may use
`provider: {use: name}` and an agent may use `memory: {use: name}`. Both are
resolved centrally and can be overridden with `WORKFLOW_PROVIDERS__...` and
`WORKFLOW_MEMORIES__...` environment variables.

An agent may also declare `sub_agents`, each with its own agent characteristics
and optional `name`. The translator builds an ADK coordinator tree; team
members use ADK's chat-mode `transfer_to_agent` mechanism. Sub-agent outputs do
not become workflow state keys unless an explicit `output_key` is configured.

An agent may declare `request_input` to expose a `request_input` tool. The first
call raises a durable `human_input` suspension; resume the same run with
`run_workflow(..., resume=True, resume_input=...)`. The supplied value is
returned to the agent tool call, allowing approval or other external input to
be handled without replaying earlier workflow tasks.
