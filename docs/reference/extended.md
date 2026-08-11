# Extended mode reference

Extended mode is the ADK-native flavor of OpenWorkflow. It adds the `agent:`
task extension and lets workflows configure ADK models, providers, tools,
memory, and agent teams inline.

## `agent:` task extension

An `agent:` block turns a task into an ADK LLM agent invocation:

```yaml
document:
  dsl: '1.0.3'
  namespace: examples
  name: draft-review
  version: '1.0.0'
use:
  models:
    flash:
      provider: gemini
      model: gemini-2.5-flash
  providers:
    gemini: {}
do:
  - draft:
      agent:
        model: flash
        instruction: Draft a concise response.
        output_key: draft
  - review:
      agent:
        model: flash
        instruction: Review and improve {draft}.
        output_key: reviewed
```

An agent task can also include `wait` (e.g. `wait: {seconds: 0}`) so that the
task has a deterministic kind alongside the `agent` extension.

## Registries

`use` supports three registries that agents can reference by name:

- `use.models` — named `ModelSpec` objects pointing to a provider and model.
- `use.providers` — provider configurations (e.g. `gemini`, `openai`).
- `use.memories` — memory backends referenced by agent tasks.

Example:

```yaml
use:
  models:
    flash:
      provider: gemini
      model: gemini-2.5-flash
  providers:
    gemini: {}
  memories:
    session:
      backend: inmemory
```

## Tools

Agents can declare tools by name under `agent.tools`. The tools must be
registered through the translator's function registry or available as
built-ins.

```yaml
  - lookup:
      agent:
        model: flash
        instruction: Look up the value.
        tools: [lookup]
```

## Multi-agent teams

An agent can spawn sub-agents through `agent.sub_agents`, creating a team
where the parent agent can delegate work.

```yaml
  - lead:
      agent:
        model: flash
        instruction: Coordinate the team.
        sub_agents:
          - model: flash
            instruction: Research the topic.
            name: researcher
          - model: flash
            instruction: Summarize findings.
            name: summarizer
```

## When to use extended mode

Use extended mode when you need:

- Inline ADK agent configuration.
- Tool calling, memory, or structured output from an LLM.
- Multi-agent teams.
- Tight integration with ADK runners and telemetry.

For portable, spec-pure workflows that delegate AI behavior to an external
function catalog, use [catalog mode](catalogs.md) instead.
