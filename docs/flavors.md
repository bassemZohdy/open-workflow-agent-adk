# Workflow flavors

OpenWorkflow ADK supports two ways to add AI behavior to a workflow.

| Flavor | AI boundary | Best for |
| --- | --- | --- |
| Extended | `metadata.adk.agent` on a task | ADK-native agents, tools, memory, teams, and inline instructions |
| Catalog | `call: <function>` resolved from `catalog.functions` | Spec-pure workflows that share reusable functions |

The shared pipeline is:

```text
load → validate → resolve catalogs/functions → translate → run
```

Catalog mode adds a reusable function-resolution step before the existing
`call: function` path. It does not change extended-mode agent translation.

## Selecting a flavor

The CLI and API accept `--mode auto|extended|catalog`.

`auto` is the default. It selects extended mode when an ADK agent is present
(`task.metadata.adk.agent`), and catalog mode when a workflow references a
catalog with a `functions` URI. Pass an explicit mode when a deployment wants a
hard policy.

## Extended mode example

Extended workflows use `task.metadata.adk.agent` to invoke an ADK agent inline.
Reusable models, providers, and memories are registered under
`document.metadata.adk`:

```yaml
document:
  dsl: '1.0.3'
  namespace: examples
  name: hello-agent
  version: '1.0.0'
  metadata:
    adk:
      models:
        flash:
          model: gemini-2.5-flash
          provider:
            use: gemini
      providers:
        gemini:
          type: gemini
do:
  - greet:
      wait:
        seconds: 0
      metadata:
        adk:
          agent:
            model:
              use: flash
            instruction: Greet the user by name.
            output_key: greeting
```

This encoding is valid OpenWorkflow v1.0.3: other implementors can parse the
same file and ignore the `metadata.adk` block.

Use extended mode when you need ADK agents, tools, memory, agent teams, or
inline instruction authoring.

## Catalog mode example

Catalog workflows keep AI behavior in a separate, reusable `functions` file.
The workflow itself is spec-pure OpenWorkflow:

```yaml
document:
  dsl: '1.0.3'
  namespace: examples
  name: greeting
  version: '1.0.0'
use:
  catalogs:
    shared:
      functions: functions.yaml
do:
  - greet:
      call: makeGreeting
```

`functions.yaml` defines ordinary tasks under a top-level `functions` key:

```yaml
functions:
  makeGreeting:
    set:
      greeting: '"hello"'
```

Use catalog mode when you want portable, spec-pure workflows or when multiple
workflows share the same function library.

## When to pick which

- Choose **extended** for agent-centric workflows, rich tool use, ADK memory,
  multi-agent teams, or when you want model/provider configuration inline.
- Choose **catalog** when portability and shared reusable functions matter
  more than ADK-specific agent features, or when you are integrating with an
  existing OpenWorkflow function catalog.
- Use **`auto`** to let the runtime decide from the document shape, or pass an
  explicit `--mode` to enforce a policy.

See [ADR 0008](decisions/0008-workflow-flavors.md), the
[catalog reference](reference/catalogs.md), and the
[extended reference](reference/extended.md).
