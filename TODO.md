# TODO — open-workflow-agent-adk

Forward-looking task list. Reference material in [`docs/`](docs/): [architecture](docs/reference/architecture.md),
[configuration](docs/reference/configuration.md), [extension spec](docs/reference/extension-spec.md),
[task coverage](docs/reference/task-coverage.md), [flavors](docs/flavors.md); ADRs in [docs/decisions/](docs/decisions/).
Spec baseline is v1.0.3 — run `spec-drift-check` before any schema work.

**Status:** v0.2.0 code has landed on `main` (`f78c0c1 Merge completed TODO work`) and is now
 tagged `v0.2.0`; `v0.1.0` tags the baseline commit `1897458`. The release branch was not preserved,
and the `Release` workflow (`on: push: tags: v*.*.*`) has never fired.
C1–C8 below are kept as the historical record of the v0.2.0 work; new follow-ups from the
whole-project review live in **C9–C15**. Latest cleanup pass: C9.1–C9.3, C10.1–C10.3/C10.13,
C11.1–C11.2, and C12.1–C12.8 completed; catalog `file://` URI handling fixed on Windows.

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
- [x] **C1.3** ~~Push both to `origin/agent/todo-complete-catalog-release`; draft PR targets `main`.~~
      Superseded — work landed on `main` via merge commit `f78c0c1`.

### C2 — Finish restructuring cleanup

- [x] **R4.2 Module-level cleanup.** Remove dead exports, tighten docstrings, consolidate
      near-duplicate handlers across `resources/`/`ops/`/`tools/`.
- [x] **R6.1 Confirm CI green on the release branch** after C1 lands (`.github/workflows/ci.yml`) —
      superseded by later CI runs on `main`; the original run ID is no longer verifiable.
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
      *(Follow-up)* `resources/catalog.py:72` now uses `url2pathname` so `file://` URIs resolve
      correctly on Windows (e.g., `file:///C:/...`); previously `Path(unquote(parsed.path))` dropped
      the leading slash and misidentified the path as outside the catalog root.

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

---

## Post-review follow-ups (C9–C13)

Findings from a whole-project review (code + structure + docs). Each item cites the evidence.
Priorities: **P0** = security/release-blocking, **P1** = correctness/hygiene, **P2** = nice-to-have.

### C9 — Reconcile TODO accuracy & finalize the v0.2.0 release  *(P0)*

The historical C1–C8 record asserts a release state that does not exist in git.

- [x] **C9.1 Create the missing git tags.** Tagged `1897458` as `v0.1.0` and `f78c0c1` as
      `v0.2.0`; pushed both tags to `origin`.
- [x] **C9.2 Drop the `agent/todo-complete-catalog-release` citations.** Removed the branch name
      from the status line and marked the C1.3 and R6.1 references as superseded.
- [x] **C9.3 Remove the unverifiable CI run-ID.** Removed the `31398202243` reference from R6.1;
      the original run is no longer verifiable.
- [ ] **C9.4 Decide whether the Release workflow has ever published.** `.github/workflows/release.yml`
      triggers on `v*.*.*` tags, but no tags exist → PyPI publish has never fired. Confirm whether
      v0.2.0 was intended to ship and, if so, run the tag + publish flow.

### C10 — Security findings from code review  *(P0/P1)*

Verified by direct read. The runtime executes arbitrary code and fetches remote resources, so these
gates matter. (C6 below the line is the prior hardening pass; these are new gaps.)

- [x] **C10.1 (P0) MCP stdio subprocess leaks the full environment.** `tasks/events.py:172` now
      builds the child environment the same way `tasks/run.py` does, stripping any
      `WORKFLOW_SECRET__*` variables before spawning the MCP stdio subprocess.
- [x] **C10.2 (P0) `resolve_secret` falls back to raw env vars.** `security/security.py:17` now
      returns only `WORKFLOW_SECRET__<name>` values. The bare-name fallback is gated behind the
      explicit `WORKFLOW_SECRETS_ALLOW_RAW=1` opt-in. Regression tests added in
      `tests/security/test_security.py`.
- [x] **C10.3 (P0) OpenAPI call endpoint is never egress-checked.** `tasks/events.py` now calls
      `validate_egress(endpoint)` after path-parameter substitution and before the outgoing HTTP
      request.
- [ ] **C10.4 (P1) `validate_egress` does not resolve DNS.** `security/security.py:53–56` returns
      early for non-IP-literal hostnames, so `metadata.google.internal` passes, then resolves to a
      private IP at fetch time. Add optional DNS resolution and check all resulting IPs, or document
      the limitation and require external DNS policy.
- [ ] **C10.5 (P1) gRPC proto compilation imports generated code in-process.** `tasks/call.py:100–120`
      writes attacker-controllable proto bytes, runs `protoc`, then `importlib.import_module`s the
      generated `_pb2*.py`. Compiled output executes on import, and the fixed module name
      `workflow_call_pb2` collides under concurrent gRPC calls. Document the trust requirement, use
      unique module names (hash suffix), and prefer a subprocess with resource limits.
- [ ] **C10.6 (P1) Script `source` can read arbitrary local files.** `tasks/run.py:148–151` only
      rejects paths not starting with `/` or `.`, so `source: /etc/shadow` or `../../.env` is
      readable via `Path(source).read_text()` outside the subprocess sandbox. Constrain to a
      configurable base dir (mirror catalog's `base_dir` pattern) or document as unrestricted.
- [ ] **C10.7 (P1) Container task mounts are unrestricted.** `tasks/run.py:63,82–85` calls
      `docker.from_env()` and defaults bind mode to `"rw"` with no host-path validation. In a CI/CD
      context with socket access this enables host escape. Default to `"ro"`, validate host paths
      against an allowlist, and consider making the Docker feature an opt-in extra.
- [ ] **C10.8 (P1) `_evaluation_budget` is a no-op on Windows.** `expressions.py:47` gates on
      `os.name == "posix"` — on Windows, JSONata expressions have no timeout (DoS vector). The
      project supports Windows (`>=3.10`, first-class). Implement a cross-platform timeout or
      document the platform gap.
- [ ] **C10.9 (P1) Unbounded agent sub-agent recursion.** `tasks/agent.py:110–125` assembles
      `sub_agents` with no depth limit — an adversarial or auto-generated document can trigger
      `RecursionError` and is an ASI02 (excessive agency) expansion. Add a max-depth guard (~10).
- [ ] **C10.10 (P1) SQLiteRunHistory is not thread-safe.** `ops/history.py:104` uses the default
      `check_same_thread=True` and has no internal lock; the class is exported as public API and a
      caller using `asyncio.to_thread`/`run_in_executor` will crash. Add `check_same_thread=False`
      + a lock, switch to `aiosqlite`, or document as single-thread-only.
- [ ] **C10.11 (P1) `WorkflowWorker.run_forever` has no error recovery.** `ops/worker.py:76–79`
      loops `run_once()` with no `try/except`; one transient broker error kills the worker
      permanently. Wrap with backoff + logging.
- [ ] **C10.12 (Low) AuditLog hash-chain cannot detect deletion.** `security/audit.py:47–63`
      verifies content + chaining but not gaps; an attacker with storage access can drop entries.
      Document, or add a stored count/root-hash check.
- [x] **C10.13 (Low) HTTP-client redirect consistency.** `tasks/call.py` and `tasks/events.py`
      now instantiate `httpx.AsyncClient(follow_redirects=False)` explicitly everywhere for
      defense-in-depth.

### C11 — Dependency hygiene  *(P0/P1)*

- [x] **C11.1 (P0) `hypothesis` and `mutmut` are runtime deps.** Moved both from
      `[project.dependencies]` to `[project.optional-dependencies.dev]` in `pyproject.toml`;
      `uv.lock` regenerated.
- [x] **C11.2 (P1) Add `[project.urls]`.** Added `Repository`, `Documentation`, `Changelog`, and
      `Issues` URLs to `pyproject.toml`.
- [ ] **C11.3 (P1) Verify `import openworkflow_adk` works with no optional extras.** `__init__.py`
      imports broker/provider/memory classes whose deps (`aiokafka`, `aio-pika`, `nats-py`,
      `asyncpg`, `boto3`, `docker`, `grpcio`) live in `dependencies`/`brokers`. Confirm the import
      succeeds in a minimal venv or add a smoke test.
- [ ] **C11.4 (P2) Consider lazy broker imports.** `KafkaBroker`/`RabbitMQBroker`/`NatsBroker` are
      exported from the root but need the `brokers` extra. Use `__getattr__` lazy import so
      `import openworkflow_adk` doesn't pull the heavy optional deps until a broker is used.

### C12 — Repo & documentation hygiene  *(P1)*

- [x] **C12.1 (P1) Add a committed `LICENSE` file.** Added `LICENSE` with the standard Apache-2.0
      text and copyright line for "OpenWorkflow ADK contributors".
- [x] **C12.2 (P1) Fix `.env.example:5` doc path.** Updated the comment to point to
      `docs/reference/configuration.md`.
- [x] **C12.3 (P1) Bump `AGENTS.md` status line.** Updated to "v0.2.0 delivered".
- [x] **C12.4 (P1) Align `.env.example` secret name with the catalog example.** Changed
      `.env.example:24` to `WORKFLOW_SECRET__OPENAI_KEY` to match `examples/catalog/summarize.yaml`.
- [x] **C12.5 (P1) Document example prerequisites.** Added a one-line prerequisite to each of
      `echo.yaml`, `rag.yaml`, and `approval.yaml` in `examples/README.md`.
- [x] **C12.6 (P1) Fix `examples/catalog.json` descriptions to match the YAMLs.** Rewrote the
      blurbs for `approval`, `multi-agent`, and `rag` to match the actual workflow content.
- [ ] **C12.7 (P2) `scripts/` has no index.** Add `scripts/README.md` mapping
      `check_mutation_score.py` (CI mutation job) and `fetch_schema.py` (refreshes
      `schema/vendor/1.0.3/`, currently unreferenced from CI/docs) to their use.
- [x] **C12.8 (P2) Extend `.gitignore`.** Added `.tmp-test/`, `_dist-check/`, `.idea/`, `*.whl`,
      and `*.tar.gz`.
- [ ] **C12.9 (P2) Document the format hook's bash requirement.** `.claude/settings.json` PostToolUse
      hook uses `jq`/`tr`/`case…esac` (Unix-only); the project is developed on Windows (cmd.exe).
      Note the Git Bash/WSL requirement in `AGENTS.md`, or rewrite portably.
- [ ] **C12.10 (P2) Add a `## License` section to README + an `AUTHORS`/`AUTHORS` policy.** Neither
      file mentions license or attribution; `pyproject.toml:7` cites "OpenWorkflow ADK contributors"
      with no backing file.

### C13 — Test structure & public API surface  *(P2)*

- [ ] **C13.1 Add `tests/tasks/` or document transitive coverage.** 7 modules under
      `src/openworkflow_adk/tasks/` (including the security-sensitive `events.py`, `call.py`,
      `run.py`) have no direct unit tests — they're exercised only via translator tests.
- [ ] **C13.2 Remove the empty `tests/conftest.py`** (docstring only) or add the shared fixtures it
      promises.
- [ ] **C13.3 Move `tests/eval_agent.py`** out of the tests root (breaks the `tests/<category>/`
      mirror; referenced as `tests.eval_agent` from `tests/core/test_adk_evaluation.py`).
- [ ] **C13.4 Audit `__init__.py` `__all__` (88 names).** Split infrastructure classes
      (`NodeBuilderRegistry`, `BackpressureController`, broker transports, `JsonRunLogger`,
      `WorkflowTelemetry`) into a provisional/internal namespace; keep only user-facing types at the
      root. Every exported name is a stability commitment at v0.2.0.
- [ ] **C13.5 Test or drop untested exports.** `hierarchical_pattern` (`tools/patterns.py:48`),
      `graph_to_document` (`tools/visual.py`), and several result/type classes
      (`OidcMetadata`, `AuditEntry`, `SimplificationResult`, `ModelReference`, …) have no test
      references — either add importability/behavior tests or drop from `__all__`.

### C14 — CI/CD: hygiene, supply chain, cost & performance  *(P0/P1)*

Current state: `.github/workflows/ci.yml` (7 jobs) + `release.yml`; **no dependabot, no CodeQL,
no caching, no concurrency, no path filters, no permissions block, no workflow linting, no timeouts.**
Action versions verified 2026-08-11 — re-verify quarterly (dependabot will help once C14.4 lands).

- [ ] **C14.1 (P0) Least-privilege `permissions` on ci.yml.** Only `release.yml` has a `permissions`
      block. Add top-level `permissions: contents: read` to ci.yml; escalate per-job only where
      needed (e.g. `security-events: write` for CodeQL/SARIF upload).
- [ ] **C14.2 (P0) Add CodeQL for Python.** No security-scanning workflow exists. Add
      `github/codeql-action/init@v3` + `analyze@v3` (Python needs no `autobuild` — it's interpreted),
      on push/PR to `main` + weekly cron. `permissions: security-events: write`.
- [ ] **C14.3 (P0) Add `actions/dependency-review-action@v5`** on PRs (`fail-on-severity: moderate`)
      to block new vulnerable dependencies before merge.
- [ ] **C14.4 (P0) Add `.github/dependabot.yml`** with two ecosystems: `github-actions` (bump action
      versions) and the new **`uv`** ecosystem (handles `pyproject.toml` + `uv.lock` natively; the
      legacy `pip` ecosystem does not). Weekly. Note: `uv` ecosystem is new — watch astral-sh/uv#2512
      for edge cases.
- [ ] **C14.5 (P1) Upgrade outdated actions.** `actions/checkout@v4 → v5`, `astral-sh/setup-uv@v6 → v9`
      (setup-python@v5, pypi-publish@release/v1 are current). Once C14.4 lands, consider SHA-pinning
      supply-chain-critical actions (checkout, setup-uv, pypi-publish) and letting dependabot maintain
      them.
- [ ] **C14.6 (P1) Cancel stale runs.** Add a `concurrency` group to ci.yml
      (`group: ${{ github.workflow }}-${{ github.ref }}`,
      `cancel-in-progress: ${{ github.event_name == 'pull_request' }}`). Currently every force-push
      to a PR burns a full matrix + mutation run.
- [ ] **C14.7 (P1) Enable uv caching.** Add `enable-cache: true` + `cache-dependency-glob: |
      uv.lock \n pyproject.toml` to every `setup-uv` step. Biggest single speedup; the install step
      is repeated in 7 jobs.
- [ ] **C14.8 (P1) Path filtering.** Doc/example/`*.md`-only changes currently trigger the full
      matrix + mutation + benchmark. Add `paths-ignore` or a `dorny/paths-filter` skip job.
- [ ] **C14.9 (P1) Pull mutation + benchmark off per-push.** `mutmut run` re-executes the suite many
      times — it's the most expensive job and runs on every push/PR. Move both to `schedule` (nightly)
      + `workflow_dispatch` + release tags. Add `timeout-minutes` to every job (esp. mutation: ~30)
      to cap free-tier burn.
- [ ] **C14.10 (P1) Consolidate duplicate jobs.** `adk-compat` (ci.yml:26–39) and
      `compatibility-matrix` (ci.yml:41–56) BOTH pin `adk-version: ["2.6.3"]` and both run pytest —
      the "matrix" doesn't actually vary ADK. Either delete `adk-compat`, or make
      `compatibility-matrix` genuinely vary ADK (`["2.6.0","2.6.1","2.6.2","2.6.3"]`) to justify its name.
- [ ] **C14.11 (P1) Remove redundant catalog pytest.** ci.yml:24 re-runs
      `pytest tests/resources/test_catalog.py` immediately after the full coverage pytest on L23
      (which already includes it).
- [ ] **C14.12 (P1) Standardize `uv sync` flags.** CI test jobs currently use `--locked`; the
      recommended strict mode is `uv sync --frozen --all-extras` (faster, asserts lockfile).
      Release builds should use `--frozen --no-dev`. Verify `uv.lock` is committed (it is).
- [ ] **C14.13 (P2) DRY the setup boilerplate.** The `checkout → setup-uv → setup-python → uv sync`
      sequence is repeated 7× in ci.yml. Extract a reusable workflow
      (`.github/workflows/_setup.yml`) or a composite action.
- [ ] **C14.14 (P2) Coverage upload + tighten gate.** Add `codecov/codecov-action@v5` to upload
      `coverage.xml`; bump `--cov-fail-under` from 80 → 83 to match the comment on ci.yml:22 (or
      document why 80 is the real bar). See Q4.
- [ ] **C14.15 (P2) Lint the workflows themselves.** Add `actionlint` (syntax/style) + `zizmor`
      (injection/permission patterns) as a CI job — both via `pip install`/`cargo install`. No
      official GH Actions wrap them reliably; direct install is preferred.
- [ ] **C14.16 (P2) Security findings → SARIF/code-scanning.** `pip-audit` can emit SARIF (upload via
      `github/codeql-action/upload-sarif@v3`); pin `anchore/sbom-action@v0` to a major and consider
      uploading its SBOM to the GH dependency graph. Currently findings live only in the run log.
- [ ] **C14.17 (P2) `workflow_dispatch` on ci.yml** for manual reruns, and parametrize the benchmark
      job's `--iterations`/`--max-p99-ms` via inputs.

### C15 — Release workflow hardening  *(P0 — ties to C9)*

`release.yml` has never fired (no tags exist — see C9.1/C9.4). When it does, it builds + publishes
with **no tests and no artifact validation** between tag and PyPI.

- [ ] **C15.1 (P0) Gate publish on tests.** `release.yml` runs `uv build` → `twine check` → publish
      with no test run. Add a job that runs the suite (or `needs:` the ci.yml test job) before
      `publish`. A tag push otherwise bypasses all quality gates.
- [ ] **C15.2 (P0) Tag/version consistency check.** Assert the pushed `v*.*.*` tag matches
      `pyproject.toml`'s `version` and fails early on mismatch. Blocks the C9.1 tagging.
- [ ] **C15.3 (P1) Smoke-test the built artifact.** Before publishing, install the freshly built
      wheel in a clean venv and run `owf-adk --version` + `python -c "import openworkflow_adk"`.
      Catches packaging bugs (wrong `packages=` in `[tool.hatch.build]`, missing files).
- [ ] **C15.4 (P1) Validate trusted-publishing end-to-end.** Confirm the PyPI publisher is registered
      (repo + workflow filename `release.yml` + environment name) and that a `release` GitHub
      Environment exists. Since the workflow has never fired, this has never been exercised — a
      misconfig will surface only at first release.
- [ ] **C15.5 (P1) Auto-create the GitHub Release.** A tag currently publishes to PyPI but creates no
      GitHub Release/notes. Add `softprops/action-gh-release` or `gh release create` with
      auto-generated notes (the repo uses Conventional Commits per AGENTS.md).
- [ ] **C15.6 (P2) `attestations: true` is now the default** in current `pypa/gh-action-pypi-publish`
      for trusted publishing — the explicit line at release.yml:26 is redundant. Either drop it or
      keep as documentation; pick one and note it.
- [ ] **C15.7 (P2) Wire CHANGELOG to release notes.** AGENTS.md says Conventional Commits; consider
      `release-please` or an auto-changelog step so `CHANGELOG.md` and the GH Release stay in sync
      with the version bump (C4.1/C4.2 in the historical record were manual).

---

### Open questions (not yet items)

- **Q1** Is v0.2.0 meant to be a published release? If yes, C9.1 + C9.4 + C11.2 + C12.1 are blocking.
  If no (internal-only), downgrade C9/C11/C12 priority and mark the Release workflow as inert.
- **Q2** The vendored schema is OpenWorkflow v1.0.3 (per AGENTS.md). Run the `spec-drift-check` skill
  before any C10/C11 work that touches task semantics — upstream may have moved.
