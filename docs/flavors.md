# Workflow flavors

OpenWorkflow ADK supports two ways to add AI behavior to a workflow.

| Flavor | AI boundary | Best for |
| --- | --- | --- |
| Extended | `agent:` on a task | ADK-native agents, tools, memory, teams, and inline instructions |
| Catalog | `call: <function>` resolved from `catalog.functions` | Spec-pure workflows that share reusable functions |

The shared pipeline is:

```text
load → validate → resolve catalogs/functions → translate → run
```

Catalog mode adds a reusable function-resolution step before the existing
`call: function` path. It does not change extended-mode agent translation.

## Selecting a flavor

The CLI accepts `--mode auto|extended|catalog` on `owf-adk run`.

`auto` is the default. It selects extended mode when an `agent:` key is
present, and catalog mode when a workflow references a catalog with a
`functions` URI. Pass an explicit mode when a deployment wants a hard policy.

See [ADR 0008](decisions/0008-workflow-flavors.md) and the
[catalog reference](reference/catalogs.md).
