# TODO — open-workflow-agent-adk

## Status

`main` is at **v0.2.1**: the v1 workflow runtime, production hardening, tests,
Docker support, CI, and release packaging are complete.

Merged since v0.2.1:

- **Spec parity (v1.0.3)**: taskBase `if`/`input`/`output`/`export`/`timeout`,
  catch retry policies and error filters, reusable
  `use.errors`/`use.retries`/`use.timeouts`, listen
  `until`/`foreach`/`correlate`, `use.extensions` injection, and
  document-level input/output filters. See
  [`docs/reference/task-coverage.md`](docs/reference/task-coverage.md).
- **C25**: GitHub Actions supply-chain hardening (SHA-pinned actions,
  `persist-credentials: false`, job-scoped permissions). `actionlint` clean,
  Zizmor zero findings.

Known gaps (deliberately uncommitted):

- `use.catalogs` is parsed for interoperability only; runtime lookup is not
  wired (catalog mode was removed — the translator ignores it).
- `listen.to.until` nested consumption-strategy form (expression form works).
- `listen` `read: raw` mode (`data`/`envelope` work).

Reference material lives in [`docs/`](docs/):

- [Architecture](docs/reference/architecture.md)
- [Configuration](docs/reference/configuration.md)
- [Extension spec](docs/reference/extension-spec.md)
- [Task coverage](docs/reference/task-coverage.md)
- [Flavors](docs/flavors.md)
- ADRs in [docs/decisions/](docs/decisions/)

Spec baseline: **OpenWorkflow v1.0.3**. Run `spec-drift-check` before any schema work.

## Future work

These items are intentionally uncommitted in the current release line:

- **A2A adapter**: expose a workflow as an ADK-compatible agent.
- **MCP adapter**: expose workflow tasks as MCP tools.

## Archive

Completed backlog detail (C1–C25 and earlier phases) is preserved in git
history, the `v0.1.0` / `v0.2.0` / `v0.2.1` tags, and `CHANGELOG.md` (the
Unreleased section covers the post-v0.2.1 spec-parity work and C25).
