# ADR 0008: Extended and catalog workflow flavors

## Status

Accepted.

## Decision

The project supports two intentionally separate authoring flavors:

- **Extended mode** allows the `agent:` task extension and compiles agent tasks
  directly to Google ADK agents.
- **Catalog mode** keeps workflow documents spec-pure. Agentic behavior is
  represented by `call: <name>`, where the named function is loaded from a
  reusable external catalog file.

Both flavors share loading, validation, translation, runtime, and all
non-agent task builders. They diverge only when resolving named functions and
agent work. The `agent:` extension remains unchanged.

Mode selection is explicit through the library/CLI when needed, with `auto` as
the default: documents containing `agent:` use extended mode, while a catalog
with a `functions` URI selects catalog mode. Explicit mode always wins and
catalog mode rejects `agent:` keys.

The flavors are not merged into one abstraction. This keeps spec-pure catalog
documents portable and preserves the existing extended-mode public API.
