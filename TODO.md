# TODO — open-workflow-agent-adk

## Status

`main` is at **v0.2.1**: the v1 workflow runtime, production hardening, tests,
Docker support, CI, and release packaging are complete. The C24 post-review
hardening track (security, correctness, architecture) has landed.

Spec-parity track (unreleased): gap analysis against the OpenWorkflow v1.0.3
schema and fellow implementors closed the remaining runtime gaps — taskBase
`if`/`input`/`output`/`export`/`timeout`, catch retry policies and error
filters, reusable `use.errors`/`use.retries`/`use.timeouts`, listen
`until`/`foreach`/`correlate`, `use.extensions` injection, and document-level
input/output filters. See `docs/reference/task-coverage.md` for the matrix.

Remaining known gaps (deliberately uncommitted):

- `use.catalogs` runtime lookup (parsed for interoperability only).
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

## Security backlog

- [ ] **C25: harden GitHub Actions workflows against Zizmor findings** — the
  current audit reports 47 SARIF findings across `canary.yml`, `ci.yml`,
  `codeql.yml`, `dependency-review.yml`, `extended.yml`, and `release.yml`:
  - **26 `unpinned-uses` errors:** third-party actions use mutable tags such as
    `@v7`, `@v5`, `@v4`, `@v2`, or `@release/v1`. Pin each action to a full
    commit SHA and retain a safe update path through Dependabot or an
    equivalent reviewed process. Mutable tags can be retargeted after review
    and introduce a supply-chain execution risk.
  - **15 `artipacked` notes:** checkout leaves the GitHub token persisted in
    local Git configuration because `persist-credentials: false` is not set.
    Disable credential persistence in every job that does not explicitly need
    Git push credentials, reducing the chance of token exposure through later
    scripts or uploaded workspace contents.
  - **2 `template-injection` errors:** `extended.yml` interpolates manual
    benchmark inputs directly into a shell command. Pass them through `env`
    and use quoted shell variables so dispatch input cannot become shell code.
  - **2 `excessive-permissions` errors:** `release.yml` grants `contents: write`
    and `id-token: write` at workflow scope, including test and version-check
    jobs. Move permissions to the individual jobs that require them and keep
    all other jobs read-only.
  - **1 `cache-poisoning` error:** the release version-check job restores a
    shared setup-uv cache. Isolate or disable that cache for trusted release
    work, and verify that release inputs cannot be supplied by untrusted
    workflow runs.
  - **1 `superfluous-actions` note:** replace the release action that only
    creates a GitHub Release with the runner's `gh release` command, or pin and
    explicitly justify retaining the action.

  Definition of done: `actionlint` passes, Zizmor has no error-level findings,
  workflow permissions are job-scoped, checkout credential handling is
  explicit, and the complete CI/release validation suite remains green.

## Archive

Completed backlog detail (C1–C24 and earlier phases) is preserved in git history
and the `v0.1.0` / `v0.2.0` / `v0.2.1` tags.
