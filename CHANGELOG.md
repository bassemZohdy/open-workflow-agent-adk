# Changelog

## 0.2.1 — 2026-08-11

C24 post-review hardening: security, correctness, and architecture work from the
v0.2.0 review.

### Security

- **HTTP server authentication** (`C24.1`): `/run`, `/run/stream`,
  `/openapi.json`, and `/metrics` require credentials when `WORKFLOW_SERVER_API_KEY`
  or an explicit `ServerAuthConfig` is configured; `user_id` is derived from the
  credential, not the request body; binding to a non-loopback host requires auth.
- **Fail-closed egress guard** (`C24.2`): hostnames are resolved and blocked by
  default (SSRF via DNS names is denied), every redirect hop is re-validated
  through guarded httpx clients, and OAuth/gRPC targets are checked.
- **Container hardening** (`C24.3`): deny-all volume mounts, `network_mode: none`
  by default, host port publishing disabled, hard CPU/memory/pids caps.
- **Static exec configs** (`C24.4`): expression-bound `run.*` and MCP `command`
  values are rejected at translate time (prompt-injection → code-execution chain).
- **MCP stdio allowlist + kill timeout** (`C24.5`), **confined local resource
  reads** (`C24.6`), **gRPC egress/TLS/proto pinning** (`C24.7`), **defusedxml
  SAML parsing** (`C24.8`), **generic errors with correlation IDs** (`C24.9`),
  and **redacted persisted event logs** (`C24.10`).

### Correctness

- `PostgresRunHistory.record_event` appends atomically via JSONB `||` (`C24.11`).
- Blocking history/container I/O moved off the event loop (`C24.12`).
- Resume works for checkpoints nested in `do`/`try`/`fork`/`switch` (`C24.13`).
- gRPC `sys.path` cleanup race fixed (`C24.14`); history dispatch is
  method-allowlisted (`C24.15`); AsyncAPI consumer waits are bounded (`C24.16`);
  the expression time budget now actually interrupts on POSIX (`C24.17`).

### Architecture

- Layering enforced with import-linter in CI: `WorkflowRegistry` moved to core,
  `duration_seconds`/`WorkflowSuspended` promoted to core, `RunConfig` frozen
  dataclass introduced, `adk_compat.py` seam added, nightly ADK canary job
  (`C24.18`–`C24.20`).
- Public API trimmed: `__all__` now lists only the core load/run/translate/
  history surface; SSO/RBAC/audit/interop names are provisional (`C24.21`,
  `C24.22`).
- Heavy dependencies moved behind `bedrock`, `containers`, `grpc`, `redis`,
  `database`, and `all` extras (`C24.23`).
- Root `conftest.py` centralizes the Docker skip helper and registers the
  `integration` marker; CI splits fast-unit and Docker-backed integration jobs
  and tracks skip counts (`C24.24`).
- `tools/` split into `interop/` and `devtools/` with backward-compatible
  facades (`C24.25`); translator BFS uses a deque (`C24.26`);
  `(namespace_id, created_at DESC)` index added (`C24.27`); `catch`/`while`
  declared as explicit `Task` fields (`C24.28`).


## Unreleased

- **Breaking**: ADK extensions now live in OpenWorkflow-compatible metadata
  containers. Task-level config goes in `task.metadata.adk` (`agent`,
  `self_heal`); project-level registries go in `document.metadata.adk`
  (`models`, `providers`, `memories`). The legacy direct forms (`agent:`,
  `self_heal:`, `use.models:`, `use.providers:`, `use.memories:`) are removed.
- **Breaking**: Catalog mode is removed. The project now supports only the
  extended flavor; `use.catalogs` is ignored by the translator.
- Added `owf-adk export --format openworkflow` and `owf-adk lint --strict`
  helpers for interoperable pure-OpenWorkflow output.

## 0.2.0 — 2026-08-10

- Added catalog mode for spec-pure workflows with reusable external function
  catalogs and `--mode auto|extended|catalog` selection.
- Split task translation into focused builder modules and mirrored the layout
  in tests and documentation.
- Added catalog examples, flavor documentation, coverage enforcement, and
  release/CI path updates.

## 0.1.0

- Added OpenWorkflow 1.0.3 validation and ADK translation.
- Added HTTP, OpenAPI, gRPC, AsyncAPI, A2A, MCP, shell, script, container, and subflow handlers.
- Added control flow, scheduling, durable sessions, run history, diagnostics, security guards,
  Docker packaging, fixtures, and the examples gallery.

Release notes follow a semantic-versioning policy. Changes are grouped under Added, Changed,
Fixed, and Security in future releases.
