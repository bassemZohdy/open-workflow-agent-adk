# TODO — open-workflow-agent-adk

## Status

`main` is at **v0.2.1**: the v1 workflow runtime, production hardening, tests,
Docker support, CI, and release packaging are complete. The C24 post-review
hardening track (security, correctness, architecture) has landed, and the C25
workflow supply-chain hardening (action pinning, credential handling,
permission scoping) is complete.

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

Completed (C25, see Archive).

## Archive

Completed backlog detail (C1–C24 and earlier phases) is preserved in git history
and the `v0.1.0` / `v0.2.0` / `v0.2.1` tags.

**C25 — GitHub Actions supply-chain hardening (complete):** Zizmor's 47 SARIF
findings across `canary.yml`, `ci.yml`, `codeql.yml`, `dependency-review.yml`,
`extended.yml`, and `release.yml` are resolved:

- **Unpinned uses (26 errors):** every third-party action is pinned to a full
  commit SHA with a `# <tag>` version comment (Dependabot-safe update path):
  `actions/checkout` v7, `actions/setup-python` v7, `codecov/codecov-action`
  v5, `anchore/sbom-action` v0, `github/codeql-action` v4,
  `actions/dependency-review-action` v5, `astral-sh/setup-uv` v9.0.0 (was
  already pinned), and `pypa/gh-action-pypi-publish` release/v1; also pinned in
  the `.github/actions/setup-owf` composite.
- **`artipacked` (15 notes):** every checkout sets `persist-credentials: false`
  — no job needs Git push credentials.
- **`template-injection` (2 errors):** `extended.yml` benchmark dispatch
  inputs pass through `env` and are consumed as quoted shell variables.
- **`excessive-permissions` (2 errors):** `release.yml` defaults to
  `contents: read`; `id-token: write` is scoped to the publish job and
  `contents: write` to the release-notes job.
- **`cache-poisoning` (1 error):** the version-check job disables the
  setup-uv cache (`enable-cache: false`).
- **`superfluous-actions` (1 note):** `softprops/action-gh-release` is replaced
  with the runner's `gh release create` (body from the extracted CHANGELOG
  section or `--generate-notes` fallback).

  Verified: `actionlint` passes, Zizmor reports zero findings at any severity
  (including informational), and the workflow-lint CI gate (`zizmor --format
  sarif`) uploads an empty SARIF.
