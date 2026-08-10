# Agent extension versioning

The extension schema is versioned independently from the OpenWorkflow DSL. The
current extension is `1.0.0` and is backward-compatible with literal `agent`
blocks and named `use.models` references. Additive fields use a minor version;
removed or incompatible fields require a major version and a migration note.
