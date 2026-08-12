:warning: **Cleanup in progress.** Completed work through C22 has been moved to the
[archive](#archive) at the bottom of this file. The sections above the archive are the currently
open tasks.

# TODO — open-workflow-agent-adk

Forward-looking task list. Reference material in [`docs/`](docs/): [architecture](docs/reference/architecture.md),
[configuration](docs/reference/configuration.md), [extension spec](docs/reference/extension-spec.md),
[task coverage](docs/reference/task-coverage.md), [flavors](docs/flavors.md); ADRs in [docs/decisions/](docs/decisions/).
Spec baseline is v1.0.3 — run `spec-drift-check` before any schema work.

**Status:** v0.2.0 code has landed on `main` and is tagged `v0.2.0`; catalog mode was removed in a
follow-up commit. **Open: C9.4, C15.4, C16.5, C18, C21.4–C21.5, and the new C23 PostgreSQL
execution-backend track.**

---

## Open

### C9 — Reconcile TODO accuracy & finalize the v0.2.0 release  *(P0)*

- [ ] **C9.4 Decide whether the Release workflow has ever published.** Confirmed: no `v*.*.*` tags existed before the cleanup pass, so the workflow has never fired and PyPI publish has never run. Whether v0.2.0 (or a new v0.3.0) should be published is a project decision; the workflow is now hardened (C15) and ready when a tag is pushed.

### C15 — Release workflow hardening  *(P0 — ties to C9)*

- [ ] **C15.4 (P1) Validate trusted-publishing end-to-end.** Requires PyPI-side trusted-publisher registration for this repository/workflow/environment and a live tag push. The workflow configuration is correct; actual end-to-end validation can only happen during the first release.

### C16 — Best practices & architectural recommendations  *(P1/P2)*

- [ ] **C16.5 (P2) Refine public API surface area in `__init__.py`.** `openworkflow_adk/__init__.py` exports many symbols (`__all__`). Separate internal infrastructure builders/transports into an internal namespace to preserve public API stability commitments.

### C18 — Extended-flavor OpenWorkflow interoperability  *(P0)*

Focus the project on the extended flavor: OpenWorkflow v1.0.3 YAML is consumed by this ADK translator and should also be safe for other implementors (e.g., SonataFlow) to parse and ignore without error. ADK-specific configuration is added/interpreted by this translator only.

- [x] **C18.1–C18.11** Completed — see archive.

### C19 — Post-migration cleanup and bug fixes  *(P1)*

Follow-ups from the legacy-encoding removal audit. These close inconsistencies and remove dead code exposed by the migration to `metadata.adk`.

#### Code fixes

- [x] **C19.3 Resolve/validate sub-agent model references.** `_build_agent()` in `tasks/agent.py` now calls `resolve_agent_characteristics()` on each sub-agent, resolving `model: {use: name}` references. Loader validators now check sub-agent model/provider/memory references recursively.
- [x] **C19.4 Make memory-service discovery recursive.** Added `_iter_tasks()` helper in `runtime.py`; `memory_service_for_document` now finds memory references in nested `do`, `try`, `catch.do`, and `fork.branches`.
- [x] **C19.5 Make state-schema derivation recursive and cover switch cases.** `_task_keys()` now collects explicit `output_key` from nested agents via `effective_agent()` and extracts state names from `switch` case `when` expressions.
- [x] **C19.6 Make diagnostics recursive.** Refactored `lint_workflow()` to recurse into nested task containers and report agent-instruction, switch-route, and duplicate-task diagnostics at the correct paths.
- [x] **C19.7 Scope `metadata.adk` contents by location.** Split `AdkMetadata` into `TaskAdkMetadata` (task-level `agent`/`self_heal`) and `DocumentAdkMetadata` (document-level `models`/`providers`/`memories`). The loader routes each `metadata.adk` payload to the correct validator by path, and `AdkMetadata` is kept as a backward-compatible union alias.
- [x] **C19.10 Harden metadata access in loader validators.** Added `_adk_agent_payload()` helper and hardened `_registries()`; non-dict `metadata` values no longer crash custom reference validators.
- [x] **C19.8–C19.11** Completed — see archive.

#### Tests

- [x] **C19.20–C19.21** Completed — see archive.
- [x] **C19.22 Add tests for sub-agent model reference resolution/validation.** Added loader tests for invalid and valid sub-agent `model: {use: ...}` references.
- [x] **C19.23 Add tests for nested agent memory and state-schema coverage.** Covered by new tests for C19.4 (nested memory) and C19.5 (nested state schema).

### C20 — Documentation and schema hygiene  *(P1)*

Docs, editor integration, changelog, and public API cleanup.

- [x] **C20.2 Rewrite stale JSON extension schema.** `docs/schema/agent-characteristics.json` now describes the `metadata.adk` container (task-level `agent`/`self_heal` and document-level `models`/`providers`/`memories`).
- [x] **C20.3 Update ADR 0001.** Marked superseded; now describes `task.metadata.adk.agent` and rejects the legacy `agent:` key.
- [x] **C20.4 Update ADR 0005.** Now describes `document.metadata.adk.models` and the `{use: name}` reference object.
- [x] **C20.5 Update ADR 0008.** `docs/decisions/0008-workflow-flavors.md` now describes the removal of catalog mode.
- [x] **C20.6 Update upstream proposal.** `docs/proposals/0001-agent-characteristics-upstream.md` now proposes `task.metadata.adk.agent` and `document.metadata.adk` registries.
- [x] **C20.7–C20.8** Completed — see archive.
- [x] **C20.9 Mention `metadata.adk` in `CLAUDE.md`.** The architectural baseline now names the `metadata.adk` container for task-level and document-level config.
- [x] **C20.10** Completed — see archive.
- [x] **C20.11 Export `AdkMetadata`.** Added `AdkMetadata` to `openworkflow_adk.__init__.py` imports and `__all__`.

### C21 — API-first agent serving  *(P1 — strategic direction)*

Shift the primary consumption model from CLI-driven workflow execution to API-calling agents/workflows. Reuse ADK-native protocol support instead of building custom interface layers.

- [x] **C21.1–C21.3, C21.6–C21.7** Completed — see archive.
- [ ] **C21.4 Wire persistent sessions/history.** Server-mode runs use `run_workflow` directly, but explicit session/history backend configuration for long-lived server processes is not yet exposed.
- [ ] **C21.5 Add protocol-specific adapters.** A2A (workflow as ADK agent), MCP (workflow tasks as tools), and OpenAPI spec generation remain future work.

### C22 — Remove catalog-mode flavor  *(P1 — strategic direction)*

The project now focuses exclusively on the extended flavor: OpenWorkflow v1.0.3 consumed by the ADK translator with ADK config in `metadata.adk`. The spec-pure catalog flavor (external function files referenced by `use.catalogs.<name>.functions`) is no longer supported. Documents may still contain `use.catalogs` per the upstream schema, but the translator ignores them.

- [x] **C22.1–C22.8** Completed — see archive.

---

### C23 — PostgreSQL execution backend and stats  *(P1/P0 — strategic direction)*

The upstream [OpenWorkflow](https://openworkflow.dev/docs/postgres) reference implementation uses a PostgreSQL backend to store workflow execution state and statistics (`workflow_runs` and `step_attempts` tables), with namespace/schema isolation, migrations, connection pooling, worker polling/claiming through the database, heartbeats, crash recovery, a dashboard, and Prometheus metrics.

This project currently has `InMemoryRunHistory` and `SQLiteRunHistory`, plus a broker-driven `WorkflowWorker`. `asyncpg` is already a runtime dependency, and `testcontainers[postgres]` is in the dev extras. The goal is to add a PostgreSQL-backed execution store that matches the upstream reference functionality so runs, steps, retries, and failures are durable and queryable for stats/observability.

- [x] **C23.1 Audit the upstream PostgreSQL backend.** Audited upstream `packages/openworkflow/postgres/backend.ts` and `postgres.ts`; documented schema, tables, indexes, namespace/schema isolation, migration strategy, and query patterns in `docs/decisions/0009-postgres-backend.md`.
- [x] **C23.2 Design the ADK-aligned PostgreSQL schema.** ADR 0009 maps upstream concepts to this translator and decides on JSONB for state/event data with normalized columns for query/filter fields (`status`, `workflow_name`, `available_at`, `created_at`).
- [x] **C23.3 Add `PostgresRunHistory`.** Added `PostgresRunHistory` in `openworkflow_adk/ops/postgres_history.py` using `asyncpg`, configurable schema/namespace, idempotent migrations, and `workflow_runs` table. The runtime now bridges sync and async history implementations. Tests use testcontainers-postgres and skip when Docker is unavailable.
- [x] **C23.4 Split step attempts into a separate table.** Added `step_attempts` table via migration 2 with FK to `workflow_runs` and indexes on `(namespace_id, run_id, created_at)` and `(namespace_id, run_id, step_name, created_at)`. `PostgresRunHistory.checkpoint()` records a `running` step attempt and `finish()` records the terminal outcome. Added `record_step_attempt()` and `list_step_attempts()` methods plus tests.
- [x] **C23.5 Add worker database-polling mode.** Added `PostgresPollingWorker` in `openworkflow_adk/ops/polling_worker.py`. It uses `PostgresRunHistory.enqueue_run()`, atomic `claim_run()`, `extend_lease()` heartbeats, and `release_run()` to execute workflows directly from the PostgreSQL queue. Exported from `openworkflow_adk`. Tests cover claim/execute, no-work, concurrent polling, and lease extension.
- [x] **C23.6 Add heartbeats and crash recovery.** `PostgresPollingWorker` already heartbeats via `extend_lease()` while executing. `claim_run()` now considers both `pending` runs and `running` runs whose `available_at` lease has expired, allowing orphaned runs to be reclaimed by another worker. Added a test that verifies lease expiry and reclamation.
- [x] **C23.7 Add query helpers for execution stats.** Added `PostgresRunHistory.stats_summary()` (counts by status plus p50/p95/p99 duration percentiles) and `failure_summary()` (recent failed runs with error text). Both support filters by workflow, workflow_namespace, status, and time range.
- [ ] **C23.8 Add Prometheus-compatible metrics endpoint.** Expose run totals, step attempt totals, failures, retries, and in-flight runs from the PostgreSQL backend.
- [ ] **C23.9 Add CLI subcommands for worker and dashboard.** `owf-adk worker start` (poll DB or consume broker) and `owf-adk dashboard` (read-only web UI or metrics endpoint).
- [ ] **C23.10 Add PostgreSQL backend tests.** Use `testcontainers-postgres` to test migrations, run lifecycle, step attempts, retries, namespace isolation, crash recovery, and metrics.

---

## Archive

Per-task detail is in git history + the `v0.1.0`/`v0.2.0` tags; design rationale in the linked ADRs.

### Delivered (compact record)

- **v1 core** (Phases 0–11 + 2A/2B/2C) — translator spine, full task coverage (`call`/`run`/`switch`/`fork`/`try`/`for`/`emit`/`listen`/…), 3-layer config, `use.models`/`use.providers`/`use.memories`. ADRs [0001](docs/decisions/0001-agent-characteristics-key.md)–[0005](docs/decisions/0005-model-reference.md).
- **Production hardening** (Phases 12–20) — telemetry, durability/resume, security sandboxing + egress guards, operability (registry/linter/plan/replay), eval/benchmarks, extensibility (tools, multi-agent, HITL, plugins, brokers), DX (schema/editor/graph/examples), spec evolution, release. ADRs [0006](docs/decisions/0006-memory-backends.md)–[0007](docs/decisions/0007-provider-adapters.md).
- **Strategic capabilities** (Phases 21–27) — AI-native (NL→workflow, self-heal, LLM routing), advanced agents (memory, multi-modal, streaming, cost caps), distributed workers, UI API, enterprise (RBAC/SSO/audit/residency/air-gap), interop (Temporal/Argo/Airflow, conformance), ecosystem.
- **Restructuring** (R1–R3, R4.1/4.3/4.4, R5, R6.2–6.4, R7.2) — core at package root, peripherals in `resources/ ops/ security/ tools/`, per-task builders in `tasks/`; `tests/` + `docs/` mirrored.
- **Catalog mode** (B0–B6) — spec-pure flavor: `call: <name>` resolves against a resource catalog whose `functions` property is a URI to an external file, shared across workflows. ADR [0008](docs/decisions/0008-workflow-flavors.md). *(Removed under C22.)*

### Completed task sections

- **C1–C8** — restructuring, catalog mode polish, release, security hardening, Docker posture, test/type discipline.
- **C9.1–C9.3** — git tags, branch citations, CI run-ID cleanup.
- **C10.1–C10.14** — MCP env, secret resolution, egress checks, DNS resolution, gRPC isolation, script/container guards, cross-platform timeouts, recursion limits, SQLite thread safety, worker recovery, audit hash chain, redirect consistency, Windows test commands.
- **C11.1–C11.4** — dependency hygiene (`hypothesis`/`mutmut` to dev, `[project.urls]`, lazy broker imports).
- **C12.1–C12.10** — LICENSE, `.env.example`, `AGENTS.md`, example prerequisites, `scripts/README.md`, `.gitignore`, format-hook docs, README license section.
- **C13.1–C13.5** — task tests, empty conftest removal, eval agent move, internal namespace, public API tests.
- **C14.1–C14.17** — CI permissions, CodeQL, dependency review, dependabot, action upgrades, concurrency, uv caching, path filtering, extended workflows, job consolidation, redundant pytest removal, `uv sync` flags, composite setup action, codecov, workflow linting + SARIF, workflow dispatch.
- **C15.1–C15.3, C15.5–C15.7** — release gates, version check, smoke test, auto release notes, CHANGELOG release body.
- **C16.1–C16.4** — path traversal, gRPC isolation, worker recovery, cross-platform JSONata timeouts.
- **C17.1–C17.10** — flavor gaps; superseded by C22 when catalog mode was removed.
- **C18.1–C18.11** — extended-flavor interoperability: `metadata.adk` encoding, loader validation, translator updates, examples, round-trip tests, export/lint helpers, legacy removal.
- **C19.1–C19.6, C19.8–C19.11, C19.20–C19.23** — diagnostic path, recursive memory-service discovery, recursive state-schema derivation, recursive diagnostics, sub-agent model reference resolution/validation, agent boolean removal, legacy rejection, CLI catalog-mode reconciliation, rejection tests, agent-boolean tests, sub-agent reference tests.
- **C20.1–C20.11** — VS Code snippet, stale JSON extension schema rewrite, ADR 0001/0005/0008 updates, upstream proposal update, `.env.example` comments, configuration doc fix, CHANGELOG entry, `CLAUDE.md` metadata mention, `AdkMetadata` export.
- **C21.1–C21.3, C21.6–C21.7** — HTTP/REST server decision, `owf-adk serve`, request/response shape, localhost defaults, server tests.
- **C22.1–C22.8** — catalog mode removal: runtime/registry, CLI, models, loader, tests, examples, docs, lockfile + green verification.
