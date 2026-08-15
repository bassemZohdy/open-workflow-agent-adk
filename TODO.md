:white_check_mark: **Backlog through C23 verified:** all tracked implementation and cleanup work through C23 is
complete on `main`. **C24 (post-review hardening)** below is the currently open work; the rest of this
file is retained as the project history and decision record.

# TODO — open-workflow-agent-adk

Historical task list and completion record. Reference material in [`docs/`](docs/): [architecture](docs/reference/architecture.md),
[configuration](docs/reference/configuration.md), [extension spec](docs/reference/extension-spec.md),
[task coverage](docs/reference/task-coverage.md), [flavors](docs/flavors.md); ADRs in [docs/decisions/](docs/decisions/).
Spec baseline is v1.0.3 — run `spec-drift-check` before any schema work.

:white_check_mark: **Status:** v0.2.0 code has landed on `main` and is tagged `v0.2.0`; catalog mode was removed in a
follow-up commit. **The currently open work is C24 (post-review hardening)**; A2A/MCP protocol
adapters remain explicitly uncommitted future work.

---

## Completed backlog

### C9 — Reconcile TODO accuracy & finalize the v0.2.0 release  *(P0)*

- [x] **C9.4 Decide whether the Release workflow has ever published.** Decision recorded: no `v*.*.*` tags existed before the cleanup pass, so the Release workflow has never fired and PyPI publish has never run. The workflow is hardened and ready when a tag is pushed.

### C15 — Release workflow hardening  *(P0 — ties to C9)*

- [x] **C15.4 (P1) Validate trusted-publishing end-to-end — local validation done.** `uv build` succeeds, `twine check` passes on both sdist and wheel, and a fresh venv smoke-installs the wheel and runs `owf-adk --version`. The final PyPI trusted-publisher handshake can only be verified during the first live release, which requires PyPI-side registration for this repository/workflow/environment and a tag push.

### C16 — Best practices & architectural recommendations  *(P1/P2)*

- [x] **C16.5 (P2) Refine public API surface area in `__init__.py`.** Moved internal infrastructure builders/transports (`build_workflow`, `create_llm`, `create_memory_service`, `memory_service_for_document`, `resolve_*`, `WorkflowWorker`, `PostgresPollingWorker`, `DiagnosticsServer`, `serve_stdio`, `load_schema`, `spec_drift_check`) to `openworkflow_adk.internal`. Root `__all__` now exposes the stable public surface; tests updated to import internals from the provisional namespace.

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
- [x] **C21.4 Wire persistent sessions/history.** The FastAPI server now passes `app.state.history` into `run_workflow` for both `/run` and `/run/stream`, and `owf-adk serve` accepts optional `--postgres-url`, `--schema`, and `--namespace` to configure a durable backend. Added `tests/tools/test_server.py::test_run_endpoint_persists_to_postgres`.
- [x] **C21.5 Add protocol-specific adapters — OpenAPI spec generation.** Added `openworkflow_adk.tools.openapi.generate_openapi()` / `export_openapi()`, `owf-adk export --format openapi`, and a `/openapi.json` endpoint on the FastAPI server. A2A (workflow as ADK agent) and MCP (workflow tasks as tools) adapters remain uncommitted future work.

### C22 — Remove catalog-mode flavor  *(P1 — strategic direction)*

The project now focuses exclusively on the extended flavor: OpenWorkflow v1.0.3 consumed by the ADK translator with ADK config in `metadata.adk`. The spec-pure catalog flavor (external function files referenced by `use.catalogs.<name>.functions`) is no longer supported. Documents may still contain `use.catalogs` per the upstream schema, but the translator ignores them.

- [x] **C22.1–C22.8** Completed — see archive.

---

### C23 — PostgreSQL execution backend and stats  *(P1/P0 — strategic direction)*

The upstream [OpenWorkflow](https://openworkflow.dev/docs/postgres) reference implementation uses a PostgreSQL backend to store workflow execution state and statistics (`workflow_runs` and `step_attempts` tables), with namespace/schema isolation, migrations, connection pooling, worker polling/claiming through the database, heartbeats, crash recovery, a dashboard, and Prometheus metrics.

The completed implementation now complements `InMemoryRunHistory` and `SQLiteRunHistory` with a
PostgreSQL-backed execution store that matches the relevant upstream reference functionality, so
runs, steps, and failures are durable and queryable for stats and observability.

- [x] **C23.1 Audit the upstream PostgreSQL backend.** Audited upstream `packages/openworkflow/postgres/backend.ts` and `postgres.ts`; documented schema, tables, indexes, namespace/schema isolation, migration strategy, and query patterns in `docs/decisions/0009-postgres-backend.md`.
- [x] **C23.2 Design the ADK-aligned PostgreSQL schema.** ADR 0009 maps upstream concepts to this translator and decides on JSONB for state/event data with normalized columns for query/filter fields (`status`, `workflow_name`, `available_at`, `created_at`).
- [x] **C23.3 Add `PostgresRunHistory`.** Added `PostgresRunHistory` in `openworkflow_adk/ops/postgres_history.py` using `asyncpg`, configurable schema/namespace, idempotent migrations, and `workflow_runs` table. The runtime now bridges sync and async history implementations. Tests use testcontainers-postgres and skip when Docker is unavailable.
- [x] **C23.4 Split step attempts into a separate table.** Added `step_attempts` table via migration 2 with FK to `workflow_runs` and indexes on `(namespace_id, run_id, created_at)` and `(namespace_id, run_id, step_name, created_at)`. `PostgresRunHistory.checkpoint()` records a `running` step attempt and `finish()` records the terminal outcome. Added `record_step_attempt()` and `list_step_attempts()` methods plus tests.
- [x] **C23.5 Add worker database-polling mode.** Added `PostgresPollingWorker` in `openworkflow_adk/ops/polling_worker.py`. It uses `PostgresRunHistory.enqueue_run()`, atomic `claim_run()`, `extend_lease()` heartbeats, and `release_run()` to execute workflows directly from the PostgreSQL queue. Exported from `openworkflow_adk`. Tests cover claim/execute, no-work, concurrent polling, and lease extension.
- [x] **C23.6 Add heartbeats and crash recovery.** `PostgresPollingWorker` already heartbeats via `extend_lease()` while executing. `claim_run()` now considers both `pending` runs and `running` runs whose `available_at` lease has expired, allowing orphaned runs to be reclaimed by another worker. Added a test that verifies lease expiry and reclamation.
- [x] **C23.7 Add query helpers for execution stats.** Added `PostgresRunHistory.stats_summary()` (counts by status plus p50/p95/p99 duration percentiles) and `failure_summary()` (recent failed runs with error text). Both support filters by workflow, workflow_namespace, status, and time range.
- [x] **C23.8 Add Prometheus-compatible metrics endpoint.** Added `/metrics` to the FastAPI server in `openworkflow_adk/server.py`. When a `PostgresRunHistory` is configured it emits `owf_adk_runs_total`, `owf_adk_run_duration_seconds`, and `owf_adk_run_failures_total`. Added `_prometheus_metrics()` helper and tests.
- [x] **C23.9 Add CLI subcommands for worker and dashboard.** Added `owf-adk worker start` (poll DB) and `owf-adk dashboard` (serve read-only metrics endpoint) in `openworkflow_adk/cli.py`; tests in `tests/tools/test_cli_worker.py`.
- [x] **C23.10 Add PostgreSQL backend tests.** `testcontainers-postgres` tests cover migrations, run lifecycle, step attempts, namespace isolation, crash recovery/lease reclamation, stats/failure summaries, and the Prometheus `/metrics` endpoint. Retries are not yet implemented at the runtime level, so no separate retry test was added.

---

## Open

### C24 — Post-review hardening  *(P0–P2 — from the v0.2.0 code/security/architecture review)*

Findings from a three-track review (code correctness, security audit, architecture) of the v0.2.0 tree.
Sequencing recommendation at the bottom; security items in C24.1–C24.4 should land before any
non-loopback deployment or release publicity.

#### Security *(P0)*

- [ ] **C24.1 Add authentication to the HTTP server.** All endpoints (`/run`, `/run/stream`, `/openapi.json`, `/metrics`) in `server.py` are unauthenticated, and `/run` executes full workflows (shell/container/MCP) with a client-supplied `user_id`. Wire the existing `AccessPolicy`/`Principal`/OIDC primitives into the FastAPI app: reject unauthenticated requests with 401, derive identity from credentials (API key/OIDC) instead of the request body, and document that `--host` other than 127.0.0.1 requires auth.
- [ ] **C24.2 Make the egress guard fail closed.** `security/security.py` bypasses private/loopback/link-local blocking for any non-IP hostname unless `WORKFLOW_EGRESS_RESOLVE_DNS=1` is set — an SSRF window via DNS names (e.g. a name resolving to `169.254.169.254`). Default to resolve-and-block, validate at connect time (httpx event hooks, closing the resolve-then-connect rebinding gap), and re-validate every redirect hop including OAuth token URLs (`tasks/simple.py`, `security/auth.py`).
- [ ] **C24.3 Harden container tasks.** `tasks/run.py` runs containers with no volume allowlist by default (empty `WORKFLOW_CONTAINER_VOLUME_ALLOWLIST` permits any host path, `rw` mode), no `network_mode` restriction, no CPU/memory/pids limits, and host port publishing. Default to deny-all volume mounts, `network_mode: none` unless explicitly overridden, and hard resource caps.
- [ ] **C24.4 Block the prompt-injection → code-execution chain.** Workflow state (which includes HTTP/tool/MCP/LLM output written via `output_key`) is expression-bound into exec-family configs (`run.command`, `run.container`, MCP `command`) with no trust-boundary check. Reject expression-bound exec configs at translate time (static analysis) and gate agent-derived values before they reach exec/egress config.
- [ ] **C24.5 Sandbox and bound MCP stdio transports.** `tasks/events.py` spawns a document/state-controlled `command` with no allowlist and an unbounded `await proc.wait()`. Allowlist MCP server commands and enforce a kill timeout.
- [ ] **C24.6 Confine local resource reads in `call` tasks.** `_read_resource`/`_read_resource_bytes` (`tasks/call.py`) read any local file with no base-dir confinement (unlike script resolution in `run.py`). Mirror the `_resolve_script_source` confinement.
- [ ] **C24.7 Egress-check and encrypt gRPC calls.** `tasks/call.py` uses `insecure_channel` (plaintext) and never runs `validate_egress` on `service.host`; proto sources are fetched from URLs and compiled with a trusted-input assumption. Egress-check the host, support TLS, and pin proto sources.
- [ ] **C24.8 Parse SAML metadata with `defusedxml`.** `security/sso.py` uses stdlib `ET.fromstring` (entity-expansion/XXE). Switch to `defusedxml.ElementTree`.
- [ ] **C24.9 Stop returning `str(exc)` to HTTP/SSE clients.** `/run` and `/run/stream` surface internal exception text (paths, URLs, response fragments). Return a generic error with a correlation ID and log the detail server-side through the redaction path.
- [ ] **C24.10 Redact persisted event logs.** Per-event history records (`_event_log_entry` in `runtime.py`) store output/state deltas unredacted while checkpoints are redacted — secrets fetched mid-run land in SQLite/Postgres, and resumed runs consume redacted state. Apply `redact()` to event-log entries and keep secrets out of resumable state by reference.

#### Correctness *(P0/P1)*

- [ ] **C24.11 Make `PostgresRunHistory.record_event` atomic.** Current read-modify-write on the whole `event_log` JSONB (`postgres_history.py`) loses events under concurrent callers and re-serializes the full log per append. Use `UPDATE ... SET event_log = event_log || $1::jsonb`.
- [ ] **C24.12 Get blocking I/O out of async paths.** `SQLiteRunHistory` (sync `sqlite3`) called from async `run_workflow` blocks the event loop; the container builder uses the blocking Docker SDK inside `async def`. Wrap in `asyncio.to_thread()` (or document sync-only) and null-check `attach_socket()` results.
- [ ] **C24.13 Support resume for nested tasks.** Resume matches `prior.checkpoint_task` against top-level `document.do` names only and slices linearly — checkpoints inside nested `do`/`fork`/`switch` raise `KeyError`, inconsistent with the recursive discovery added under C19. Reuse `_iter_tasks()` recursion or document resume as top-level-only.
- [ ] **C24.14 Fix `sys.path` race in the gRPC builder.** `tasks/call.py` inserts/removes `sys.path` entries without guarding concurrent calls; wrap the removal in `try/except ValueError`.
- [ ] **C24.15 Add a method allowlist to `_call_history_method`.** `runtime.py` dispatches history calls by unvalidated string `getattr`. Allowlist known method names.
- [ ] **C24.16 Add a timeout to the AsyncAPI consumer loop.** `tasks/events.py` `while True: await broker.consume()` hangs forever if no matching event arrives. Wrap in `asyncio.wait_for` using `task.timeout` or a default.
- [ ] **C24.17 Verify the expression budget actually interrupts on POSIX.** The `SIGALRM` handler in `expressions.py` uses a generator-throw lambda that may not raise in the evaluating frame. Test with a pathological expression; fix via a flag-check or setitimer pattern if it doesn't fire.

#### Architecture & maintainability *(P1/P2)*

- [ ] **C24.18 Fix the inverted dependency direction and enforce layering.** `runtime.py`/`translator.py` import `tools.registry` while other `tools/*` and `ops/*` modules import `runtime`/`translator` — the intended layering survives by accident. Move `WorkflowRegistry` to core, split `ops` into infra (below core) and services (above core), and add an `import-linter` contract wired into CI.
- [ ] **C24.19 Add an ADK compatibility seam and a real canary.** 9 modules import private `google.adk.workflow._*` APIs; the compatibility-matrix CI job only tests the pinned version against itself (zero information). Consolidate ADK imports behind one `adk_compat.py` and add a nightly canary job running the suite against latest ADK.
- [ ] **C24.20 Introduce a `RunConfig` dataclass.** `run_workflow` takes 27 keyword params re-threaded through `build_workflow` and `NodeBuilderRegistry`; every new capability costs 4 signature edits. Consolidate into one frozen config object and extract resume/session-backend logic.
- [ ] **C24.21 Triage the public API before v1.0.** `__init__.py` exports ~68 names including SSO/RBAC/audit/interop surfaces — each a semver promise for a solo-maintained project. Cut to ~20 core symbols (load/validate/run/translate/history); demote the rest to `internal` or extras.
- [ ] **C24.22 Verify OIDC tokens or demote the API.** `OidcClient` exchanges codes and returns token JSON with no JWKS/signature verification; SAML support is metadata parsing only. Either implement verification or move both behind an "unverified" internal namespace with docstring warnings.
- [ ] **C24.23 Move heavy dependencies behind extras.** `boto3`, `docker`, `grpcio-tools`, `redis`, `sqlalchemy` are hard dependencies for what is primarily a translator library. Split into `bedrock`, `containers`, `grpc`, `redis` extras.
- [ ] **C24.24 Add a root `conftest.py` and integration test markers.** The Docker/testcontainers skip dance is copy-pasted across ≥6 test files with a second, inconsistent env-var gate; without Docker, Postgres tests silently skip while coverage gates stay green. Centralize the skip helper, register `pytest.mark.integration`, split CI into fast-unit and integration jobs, and track skip counts.
- [ ] **C24.25 Split the `tools/` package.** 16 modules spanning ≥5 concerns (core infra, diagnostics/devUX, interop, AI tooling, extension). Split into `interop/` and `devtools/`; keep `plugins`/`patterns` near core.
- [ ] **C24.26 Use a `deque` for translator BFS.** `pending.pop(0)` in `build_workflow` is O(n²) for large task lists.
- [ ] **C24.27 Add a `(namespace_id, created_at DESC)` index.** `list_runs` without a status filter falls back to a sequential scan in `postgres_history.py`.
- [ ] **C24.28 Declare `catch`/`while` as explicit `Task` fields.** Currently accessed via `getattr` on Pydantic extras — verified working on pydantic 2.13, but explicit fields would be cleaner and resilient to a Pydantic upgrade.

#### Security tests to add alongside C24.1–C24.10

- SSRF suite: hostname resolving to `127.0.0.1`/`169.254.169.254`, redirect-to-blocked-range with `redirect: true`, gRPC host bypass — all denied by default config.
- Prompt-injection regression: agent output containing exec-targeting instructions must not reach `run.command`/MCP command bindings.
- Container harness: volume mount outside allowlist with allowlist unset must be denied; assert `network_mode`/limit defaults.
- Auth: 401 on `/run`, `/metrics`, `/openapi.json` without credentials; `user_id` from body ignored.
- Fuzz: SAML entity expansion, oversized/deep expressions, SSE error payloads free of exception text.

**Suggested sequencing:** C24.1–C24.4 (auth + fail-closed egress, before any non-loopback binding) →
C24.11 → C24.24 → C24.18 → C24.19 → C24.20 → C24.21/C24.23 (before v1.0/PyPI publicity).

---

## Future work (not part of the completed backlog)

- A2A adapter: expose a workflow as an ADK-compatible agent.
- MCP adapter: expose workflow tasks as MCP tools.

These items are intentionally not marked complete and have no implementation commitment in the
current release line.

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
