# TODO — open-workflow-agent-adk

Delivery record. Reference material lives in [`docs/`](docs/): [architecture](docs/architecture.md),
[configuration](docs/configuration.md), [extension spec](docs/extension-spec.md),
[task coverage](docs/task-coverage.md); architectural decisions in [docs/decisions/](docs/decisions/).
Spec baseline is v1.0.3 — run `spec-drift-check` before any schema work.

**Status:** all phases delivered. Phases 0–11 + 2A/2B/2C are the v1 core; 12–20 are production
hardening; 21+ are strategic capabilities built as demand materialized. New work starts a new backlog.

---

## Phase 0 — Foundation  *(done)*

- [x] **0.1** Package skeleton — `src/openworkflow_adk/` + `pyproject.toml` entrypoint.
- [x] **0.2** uv lockfile.
- [x] **0.3** Test harness — `tests/`, pytest-asyncio.
- [x] **0.4** CI — uv + ruff + pytest on py3.10/3.11/3.12.
- [x] **0.5** Vendored v1.0.3 schema + `scripts/fetch_schema.py`.

## Phase 1 — Schema + parsing  *(done)*

- [x] **1.1** Extension-key decision → [ADR 0001](docs/decisions/0001-agent-characteristics-key.md) (dedicated `agent` key).
- [x] **1.2** Typed document model (all task types, `taskBase`, `use.*`).
- [x] **1.3** `AgentCharacteristics` extension model.
- [x] **1.4** Two-stage validator (JSON schema + extension).
- [x] **1.5** Loader API `load(source) -> OpenWorkflowDocument`.

## Phase 2 — Config resolution (3-layer)  *(done)*

- [x] **2.1** Env resolver (`WORKFLOW_` / `__`).
- [x] **2.2** Default registry.
- [x] **2.3** 3-layer merge.

## Phase 2A — Reusable model definitions (`use.models`)  *(done)*

- [x] **2A.1** `ModelSpec` + `use.models` registry.
- [x] **2A.2** Reference shape → [ADR 0005](docs/decisions/0005-model-reference.md) (`{use: name}`; back-compat literal).
- [x] **2A.3** Resolution + 3-layer precedence.
- [x] **2A.4** Translator wiring via `model_factory`.
- [x] **2A.5** Tests + docs.

## Phase 2B — Multi-provider model layer  *(done)*

- [x] **2B.1** `use.providers` registry — `ProviderConfig` (type/endpoint/secret refs).
- [x] **2B.2** Provider → `BaseLlm` adapter factory → [ADR 0007](docs/decisions/0007-provider-adapters.md).
- [x] **2B.3** Model→provider wiring via `model_factory`.
- [x] **2B.4** Env override of provider fields.
- [x] **2B.5** Tests + docs.

## Phase 2C — Pluggable memory layer  *(done)*

- [x] **2C.1** `use.memories` registry — `MemoryConfig`.
- [x] **2C.2** `BaseMemoryService` adapters (in-memory/file/redis/postgres/vertex) → [ADR 0006](docs/decisions/0006-memory-backends.md).
- [x] **2C.3** Agent `memory: {use: name}` reference.
- [x] **2C.4** Env override of memory backend.
- [x] **2C.5** Session/state parity documented (cross-link to 8.3/12.1).
- [x] **2C.6** Tests + docs.

## Phase 3 — Expression engine  *(done)*

- [x] **3.1** JSONata evaluator → [ADR 0002](docs/decisions/0002-jsonata-engine.md).
- [x] **3.2** Expression binder (`input`/`output`/`export`/`set`/`if`/`when`).

## Phase 4 — Translation core (MVP spine)  *(done)*

- [x] **4.1** Node-builder registry.
- [x] **4.2** Sequence builder (`then` continue/exit/end/goto).
- [x] **4.3** State-schema derivation.
- [x] **4.4** `set` / `wait` / `raise` nodes.
- [x] **4.5** `call: http` handler.
- [x] **4.6** Agent-task builder.
- [x] **4.7** Workflow assemble + run.

## Phase 5 — Control flow  *(done)*

- [x] **5.1** `switch`.
- [x] **5.2** `fork` (non-compete).
- [x] **5.3** `fork.compete` → [ADR 0003](docs/decisions/0003-fork-compete.md).
- [x] **5.4** `try` / `catch` → [ADR 0004](docs/decisions/0004-try-catch.md).
- [x] **5.5** `for` (+`while`).
- [x] **5.6** `do` (nested).

## Phase 6 — Remaining call/run handlers  *(done)*

- [x] **6.1** `call: openapi`.
- [x] **6.2** `call: grpc`.
- [x] **6.3** `call: asyncapi`.
- [x] **6.4** `call: a2a`.
- [x] **6.5** `call: mcp`.
- [x] **6.6** `call: function` (named).
- [x] **6.7** `run: shell`.
- [x] **6.8** `run: script`.
- [x] **6.9** `run: container`.
- [x] **6.10** `run: workflow` (subflow).

## Phase 7 — Event handling  *(done)*

- [x] **7.1** Broker adapter interface.
- [x] **7.2** `emit`.
- [x] **7.3** `listen`.
- [x] **7.4** `schedule`.

## Phase 8 — Entrypoints + runtime  *(done)*

- [x] **8.1** CLI — `owf-adk run`.
- [x] **8.2** Library API — `openworkflow_adk.run(...)`.
- [x] **8.3** Session/state backend selector.
- [x] **8.4** Error model (OpenWorkflow ↔ ADK).

## Phase 9 — Docker + deploy  *(done)*

- [x] **9.1** Dockerfile (multi-stage, uv-based).
- [x] **9.2** docker-compose (echo service + broker demos).
- [x] **9.3** Config externalization (env + secret mounting).

## Phase 10 — Tests + fixtures  *(done)*

- [x] **10.1** Golden fixtures.
- [x] **10.2** Per-handler unit tests.
- [x] **10.3** Config-layering tests.
- [x] **10.4** End-to-end tests.
- [x] **10.5** ADK-version pin + compat test.

## Phase 11 — Docs  *(done)*

- [x] **11.1** README.
- [x] **11.2** Extension spec.
- [x] **11.3** Task-coverage matrix.
- [x] **11.4** Config reference.
- [x] **11.5** ADRs (0001–0007).

---

## Post-v1 — production hardening (Phases 12–20)  *(done)*

Production-grade hardening, operability, and release packaging delivered after the v1 core.

### Phase 12 — Production readiness

- [x] **12.1** Prod session backend.
- [x] **12.2** Telemetry — OTel traces/metrics/logs, one span per task.
- [x] **12.3** Structured run logging (JSON, run-id keyed).
- [x] **12.4** Health + graceful shutdown.

### Phase 13 — Durability & resume

- [x] **13.1** Persist + resume from checkpoint (ADK replay/rehydration).
- [x] **13.2** Suspend on `listen`/`wait`.
- [x] **13.3** Checkpoint config.
- [x] **13.4** Replay-determinism property test.

### Phase 14 — Security hardening

- [x] **14.1** Sandbox code tasks (`run: shell`/`script`).
- [x] **14.2** Secret management — `use.secrets`; redaction.
- [x] **14.3** Expression safety — sandboxed JSONata eval.
- [x] **14.4** Egress guards — SSRF allowlist.
- [x] **14.5** Auth audit — every `authenticationPolicy` variant.
- [x] **14.6** Supply chain — pinned deps, SBOM, vuln scan in CI.

### Phase 15 — Operability

- [x] **15.1** Workflow registry (namespace/name/version).
- [x] **15.2** Static linter.
- [x] **15.3** Dry-run / plan — `owf-adk plan`.
- [x] **15.4** Run history + inspect.
- [x] **15.5** Replay-from-task.

### Phase 16 — Testing & evaluation depth

- [x] **16.1** Workflow test harness — `owf-adk test`.
- [x] **16.2** ADK evaluation.
- [x] **16.3** Property/mutation tests.
- [x] **16.4** Load/benchmark suite.

### Phase 17 — Extensibility

- [x] **17.1** Tool registry.
- [x] **17.2** Multi-agent teams (`sub_agents` + `transfer_to_agent`).
- [x] **17.3** Human-in-the-loop (ADK `request_input`/interrupts).
- [x] **17.4** Plugin task handlers.
- [x] **17.5** Broker adapters (Kafka/RabbitMQ/NATS/Redis Streams + CloudEvents).

### Phase 18 — Authoring & DX

- [x] **18.1** Extension JSON-schema.
- [x] **18.2** Editor integration.
- [x] **18.3** Graph preview — `owf-adk graph`.
- [x] **18.4** Examples gallery.
- [x] **18.5** Diagnostics server (optional; stdio JSON-RPC).

### Phase 19 — Spec evolution

- [x] **19.1** Multi-version support.
- [x] **19.2** Upstream-sync runbook.
- [x] **19.3** Extension versioning.
- [x] **19.4** Upstream proposal — [issue #1184](https://github.com/open-workflow-specification/specification/issues/1184).

### Phase 20 — Release & packaging

- [x] **20.1** PyPI publish (build + provenance + sign).
- [x] **20.2** Semver + changelog.
- [x] **20.3** Support window.
- [x] **20.4** Compatibility-matrix CI.

---

## Horizon 3 — strategic capabilities (Phases 21+)  *(done)*

Strategic capabilities delivered as adoption signals materialized.

### Phase 21 — AI-native workflow capabilities

- [x] **21.1** NL → workflow (validated doc generation).
- [x] **21.2** Self-healing tasks (`try.self_heal`).
- [x] **21.3** LLM-driven routing (`route_to` via `Context.route`).
- [x] **21.4** Semantic search/discovery over registry.
- [x] **21.5** Workflow simplification (auditable).

### Phase 22 — Advanced agent capabilities

- [x] **22.1** Persistent agent memory (builds on 2C).
- [x] **22.2** Multi-modal agent tasks (vision/audio).
- [x] **22.3** Streaming agent output.
- [x] **22.4** Model routing & cost caps.
- [x] **22.5** Orchestration-pattern library (map/reduce, debate, hierarchical).

### Phase 23 — Distributed execution & scale

- [x] **23.1** Distributed workers (broker-driven dispatch).
- [x] **23.2** Region affinity.
- [x] **23.3** Result memoization.
- [x] **23.4** Adaptive backpressure.

### Phase 24 — Web UI & dashboard

- [x] **24.1** Management UI API (list/run/inspect/history/graph-plan).
- [x] **24.2** Visual builder (graph → YAML).
- [x] **24.3** Live run inspector (`stream_run`).
- [x] **24.4** Template gallery.

### Phase 25 — Enterprise readiness

- [x] **25.1** RBAC.
- [x] **25.2** SSO (OIDC + SAML).
- [x] **25.3** Audit & compliance (hash-chain log).
- [x] **25.4** Data residency.
- [x] **25.5** Air-gapped deploy (`WORKFLOW_AIRGAPPED=1`).

### Phase 26 — Interoperability

- [x] **26.1** Export → Temporal.
- [x] **26.2** Import ← Argo / Airflow.
- [x] **26.3** Cross-runtime portability report.
- [x] **26.4** Conformance review request — [issue #1185](https://github.com/open-workflow-specification/specification/issues/1185).

### Phase 27 — Ecosystem & community

- [x] **27.1** Plugin registry (trusted-digest discovery).
- [x] **27.2** Contribution governance (RFC, SLAs).
- [x] **27.3** Hosted docs site.
- [x] **27.4** Adoption instrumentation (opt-in).
