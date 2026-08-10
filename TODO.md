# TODO — open-workflow-agent-adk

Forward-looking task list. Reference material in [`docs/`](docs/): [architecture](docs/reference/architecture.md),
[configuration](docs/reference/configuration.md), [extension spec](docs/reference/extension-spec.md),
[task coverage](docs/reference/task-coverage.md), [flavors](docs/flavors.md); ADRs in [docs/decisions/](docs/decisions/).
Spec baseline is v1.0.3 — run `spec-drift-check` before any schema work.

**Status:** `v0.2.0` is tagged and pushed on the
`agent/todo-complete-catalog-release` branch. Local and remote CI are suite-green; the draft PR
targets `main`.

---

## Delivered (compact record)

Per-task detail is in git history + the `v0.1.0` tag; design rationale in the linked ADRs.

- **v1 core** (Phases 0–11 + 2A/2B/2C) — translator spine, full task coverage (`call`/`run`/`switch`/
  `fork`/`try`/`for`/`emit`/`listen`/…), 3-layer config, `use.models`/`use.providers`/`use.memories`.
  ADRs [0001](docs/decisions/0001-agent-characteristics-key.md)–[0005](docs/decisions/0005-model-reference.md).
- **Production hardening** (Phases 12–20) — telemetry, durability/resume, security sandboxing +
  egress guards, operability (registry/linter/plan/replay), eval/benchmarks, extensibility (tools,
  multi-agent, HITL, plugins, brokers), DX (schema/editor/graph/examples), spec evolution, release.
  ADRs [0006](docs/decisions/0006-memory-backends.md)–[0007](docs/decisions/0007-provider-adapters.md).
- **Strategic capabilities** (Phases 21–27) — AI-native (NL→workflow, self-heal, LLM routing),
  advanced agents (memory, multi-modal, streaming, cost caps), distributed workers, UI API,
  enterprise (RBAC/SSO/audit/residency/air-gap), interop (Temporal/Argo/Airflow, conformance),
  ecosystem. Upstream proposals: [#1184](https://github.com/open-workflow-specification/specification/issues/1184),
  [#1185](https://github.com/open-workflow-specification/specification/issues/1185).
- **Restructuring** (R1–R3, R4.1/4.3/4.4, R5, R6.2–6.4, R7.2) — core at package root, peripherals in
  `resources/ ops/ security/ tools/`, per-task builders in `tasks/`; `tests/` + `docs/` mirrored.
- **Catalog mode** (B0–B6) — spec-pure flavor: `call: <name>` resolves against a resource catalog
  whose `functions` property is a URI to an external file, shared across workflows. ADR [0008](docs/decisions/0008-workflow-flavors.md).

---

## Remaining

### C1 — Commit & persist the uncommitted work  *(P0 — blocks everything else)*

~136 working-tree changes (the restructuring + catalog-mode tracks) are not in git. One `git clean`
or bad pull and they're gone.

- [x] **C1.1** Commit the restructuring as one focused commit (R1–R3 + R4.1/4.3/4.4 + R5 + R6.2–6.4 + R7.2).
- [x] **C1.2** Commit catalog mode as a separate logical commit (B0–B6 + `examples/catalog/` + ADR 0008).
- [x] **C1.3** Push both to `origin/agent/todo-complete-catalog-release`; draft PR targets `main`.

### C2 — Finish restructuring cleanup

- [x] **R4.2 Module-level cleanup.** Remove dead exports, tighten docstrings, consolidate
      near-duplicate handlers across `resources/`/`ops/`/`tools/`.
- [x] **R6.1 Confirm CI green on the release branch** after C1 lands (`.github/workflows/ci.yml`) —
      run `31398202243` covers both the regrouped layout and catalog mode.
- [x] **R7.1 Baseline commit message** (`1897458`) still says "v1.0.0" — tag is correct at `v0.1.0`.
      Amend + `git push --force-with-lease` only if pristine history is wanted; else leave.

### C3 — Catalog mode polish  *(audit findings)*

- [x] **C3.1 Fix misleading `endpoint` in catalog examples.** `examples/catalog/{greeting,summarize}.yaml`
      set `endpoint: https://catalog.example.invalid` (RFC-2606 non-routable) — the `functions:
      functions.yaml` URI is what actually resolves. Either drop `endpoint`, point it at `file://`,
      or document that `functions` is the operative resolver and `endpoint` is vestigial.
- [x] **C3.2 Document the secret requirement for `summarize`.** It calls OpenAI with
      `bearer: { use: openai-key }` — needs `WORKFLOW_SECRET__OPENAI_KEY` set before it runs.
      `greeting` (deterministic `set`) should run out-of-the-box; verify it does.
- [x] **C3.3 CI exercises catalog mode.** Confirm the matrix runs the B6 catalog tests on every push,
      not just the extended-mode suite.
- [x] **C3.4 Top-level README presents both flavors** — extended vs catalog, when to use each, and
      the `--mode {auto,extended,catalog}` flag (R5.1 fixed stale paths; this adds user-facing coverage).
- [x] **C3.5 Index the catalog examples** in the examples gallery / `docs/guides/`.

### C4 — Release

- [x] **C4.1 Version bump `0.1.0` → `0.2.0`** (minor: catalog mode is an additive feature) in
      `pyproject.toml` + update the `owf-adk --version` string.
- [x] **C4.2 `CHANGELOG.md`** entry for 0.2.0 (restructure + catalog mode).
- [x] **C4.3 Tag `v0.2.0`** after C1–C3 landed and CI was green; pushed the tag.

### C5 — Standing items (low urgency)

- [x] **C5.1 testcontainers skip.** The 2 skipped tests need Docker; documented in `CONTRIBUTING.md`
      — consider a non-Docker fast path so they don't skip in minimal CI runners.
- [x] **C5.2 Coverage trend.** R6.2 recorded a baseline; track the % over time in CI (defend, don't chase).

### C6 — Security hardening gaps  *(audit — untrusted-code execution path)*

The runtime executes arbitrary code (`run: shell`/`script`) and, in catalog mode, fetches remote
files. Real gaps found in code review:

- [ ] **C6.1 Default timeout for code tasks.** `tasks/run.py` enforces a timeout only when
      `task.timeout` is set — a `run: shell` without it runs unbounded. Add a configurable default
      (`WORKFLOW_RUN_DEFAULT_TIMEOUT`, e.g. 60s).
- [ ] **C6.2 Subprocess env sanitization.** `tasks/run.py` passes `env={**os.environ, …}` to the
      child — it inherits `WORKFLOW_SECRET__*` and any credentials, so a hostile script can exfiltrate
      them. Strip secret-prefixed vars before `create_subprocess_exec`.
- [ ] **C6.3 Network sandbox gap.** `_sandbox_preexec` (`tasks/common.py`) sets rlimits + no-new-privs
      but does no network isolation — sandboxed scripts can still open outbound sockets. Document the
      resulting threat-model limit, or add seccomp / network-namespacing.
- [ ] **C6.4 Catalog URI fetcher SSRF.** `resources/catalog.py` calls `validate_egress` pre-fetch,
      but `httpx.get` follows redirects (302 → internal host bypasses the allowlist) and the `file://`
      path has no traversal guard. Disable redirects + revalidate the final URL; constrain `file://`
      to an allowlist root.

### C7 — Docker posture

- [ ] **C7.1 Run as non-root.** `Dockerfile` has no `USER` directive — the container executes
      arbitrary `run: shell`/`script` code as root. Add a non-root user.
- [ ] **C7.2 `.dockerignore`.** Missing — the build context drags in `docs/`, `.github/`, test
      artifacts; bloats the image and leaks dev files into the context.
- [ ] **C7.3 Don't ship `TODO.md`.** `COPY README.md TODO.md ./` puts a dev artifact in the runtime
      image. Copy only what the runtime needs.
- [ ] **C7.4 `HEALTHCHECK`.** Phase 12.4 delivered health/readiness, but the `Dockerfile` ships no
      `HEALTHCHECK` directive.
- [ ] **C7.5 `docker-compose.yml` hardening.** No `read_only`, `cap_drop: ALL`, or `security_opt` —
      and the compose runs workflows that may exec code.

### C8 — Test & type discipline

- [ ] **C8.1 Catalog-mode test coverage.** Only `tests/resources/test_catalog.py` covers a whole new
      flavor (URI fetch, registry, restricted validation, e2e). Add: HTTP fetch (mocked), redirect-
      SSRF attempt, `file://` traversal attempt, cross-workflow sharing, precedence-on-collision.
- [ ] **C8.2 Type-discipline pass.** 103 `Any` / `type: ignore` sites in a `py.typed` package —
      tighten where cheap, document where intentional. Defend the public-API boundary first.
