# ADR 0005: Named model bundles use an explicit reference object

## Decision

Agent characteristics accept either a literal model string or
`model: {use: <name>}`. The object form resolves against the workflow's
`use.models` registry; a bare model name is always treated as a literal model ID.

## Rationale

An explicit object avoids ambiguity between a provider model ID and a registry
entry while allowing a centrally managed generation configuration bundle.

## Consequences

Named bundle fields are resolved first, task-level fields override the bundle,
and environment variables under `WORKFLOW_MODELS__<NAME>__...` can repoint a
bundle for deployment-specific configuration.
