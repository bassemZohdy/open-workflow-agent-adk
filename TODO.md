# TODO — open-workflow-agent-adk

## Status

`main` is at **v0.2.1**: the v1 workflow runtime, production hardening, tests,
Docker support, CI, and release packaging are complete. The C24 post-review
hardening track (security, correctness, architecture) has landed.

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

Completed backlog detail (C1–C24 and earlier phases) is preserved in git history
and the `v0.1.0` / `v0.2.0` / `v0.2.1` tags.
