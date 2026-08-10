# TODO — open-workflow-agent-adk

Forward-looking task list. Reference material in [`docs/`](docs/): [architecture](docs/reference/architecture.md),
[configuration](docs/reference/configuration.md), [extension spec](docs/reference/extension-spec.md),
[task coverage](docs/reference/task-coverage.md), [flavors](docs/flavors.md); ADRs in [docs/decisions/](docs/decisions/).
Spec baseline is v1.0.3 — run `spec-drift-check` before any schema work.

**Status:** `v0.2.0` is tagged on `agent/todo-complete-catalog-release` (CI green), but **`main` is
5 commits behind and there is no open PR** — the release has not landed on `main`. See **C9**.

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

- [x] **C6.1 Default timeout for code tasks.** `WORKFLOW_RUN_DEFAULT_TIMEOUT` defaults to 60 seconds
      and applies when a task does not define its own timeout.
- [x] **C6.2 Subprocess env sanitization.** `run.py` strips `WORKFLOW_SECRET__*` from the child
      environment, including task-provided environment overrides.
- [x] **C6.3 Network sandbox gap.** Documented in [security.md](docs/reference/security.md): the
      best-effort sandbox does not isolate network access; deployment policy is required.
- [x] **C6.4 Catalog URI fetcher SSRF.** Redirects are disabled and local catalog paths are constrained
      to the workflow catalog base directory; regression tests cover redirect and traversal attempts.

### C7 — Docker posture

- [x] **C7.1 Run as non-root.** The runtime image creates and selects the unprivileged `workflow` user.
- [x] **C7.2 `.dockerignore`.** Build context excludes source-control, docs, tests, caches, and artifacts.
- [x] **C7.3 Don't ship `TODO.md`.** The runtime image copies only `README.md` as project documentation.
- [x] **C7.4 `HEALTHCHECK`.** The image checks the installed CLI version at regular intervals.
- [x] **C7.5 `docker-compose.yml` hardening.** Services use read-only filesystems, drop all
      capabilities, and enable `no-new-privileges`.

### C8 — Test & type discipline

- [x] **C8.1 Catalog-mode test coverage.** Added mocked HTTP redirect protection, `file://` traversal,
      registry sharing, and collision/precedence coverage alongside the existing catalog tests.
- [x] **C8.2 Type-discipline pass.** Documented the intentional dynamic adapter boundaries and policy
      for keeping public APIs model-typed in [type-discipline.md](docs/reference/type-discipline.md).
