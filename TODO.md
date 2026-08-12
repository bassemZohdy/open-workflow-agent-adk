# TODO — open-workflow-agent-adk

Forward-looking task list. Reference material in [`docs/`](docs/): [architecture](docs/reference/architecture.md),
[configuration](docs/reference/configuration.md), [extension spec](docs/reference/extension-spec.md),
[task coverage](docs/reference/task-coverage.md), [flavors](docs/flavors.md); ADRs in [docs/decisions/](docs/decisions/).
Spec baseline is v1.0.3 — run `spec-drift-check` before any schema work.

**Status:** v0.2.0 code has landed on `main` (`f78c0c1 Merge completed TODO work`) and is now
tagged `v0.2.0`; `v0.1.0` tags the baseline commit `1897458`. The release branch was not preserved,
and the `Release` workflow (`on: push: tags: v*.*.*`) has never fired.
C1–C8 below are kept as the historical record of the v0.2.0 work; follow-ups from the whole-project
review live in **C9–C18**. Latest cleanup pass: C9.1–C9.3, C10.1–C10.14, C11.1–C11.4, C12.1–C12.10,
C13.1–C13.5, C14.1–C14.17, C15.1–C15.7, C17.1–C17.10, and C21.1–C21.3/C21.6–C21.7 completed; catalog
`file://` URI handling fixed on Windows; C10.5 gRPC proto compilation hardened. **Open: C18
(extended-flavor interoperability) and C21.4/C21.5 (server sessions + protocol adapters).**

---

## Delivered (compact record)

Per-task detail is in git history + the `v0.1.0` tag; design rationale in the linked ADRs.

- **v1 core** (Phases 0–11 + 2A/2B/2C) — translator spine, full task coverage (`call`/`run`/`switch`/
  `fork`/`try`/`for`/`emit`/`listen`/â€¦), 3-layer config, `use.models`/`use.providers`/`use.memories`.
  ADRs [0001](docs/decisions/0001-agent-characteristics-key.md)–[0005](docs/decisions/0005-model-reference.md).
- **Production hardening** (Phases 12–20) — telemetry, durability/resume, security sandboxing +
  egress guards, operability (registry/linter/plan/replay), eval/benchmarks, extensibility (tools,
  multi-agent, HITL, plugins, brokers), DX (schema/editor/graph/examples), spec evolution, release.
  ADRs [0006](docs/decisions/0006-memory-backends.md)–[0007](docs/decisions/0007-provider-adapters.md).
- **Strategic capabilities** (Phases 21–27) — AI-native (NLâ†’workflow, self-heal, LLM routing),
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

- [x] **C4.1 Version bump `0.1.0` â†’ `0.2.0`** (minor: catalog mode is an additive feature) in
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
- [ ] **C9.4 Decide whether the Release workflow has ever published.** Confirmed: no `v*.*.*` tags existed before this cleanup pass, so the workflow has never fired and PyPI publish has never run. Whether v0.2.0 (or a new v0.3.0) should be published is a project decision; the workflow is now hardened (C15) and ready when a tag is pushed.
      triggers on `v*.*.*` tags, but no tags exist â†’ PyPI publish has never fired. Confirm whether
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
- [x] **C10.4 (P1) `validate_egress` does not resolve DNS.** `security/security.py:84–92` resolves
      non-IP-literal hostnames via `socket.getaddrinfo` and checks all returned IP addresses.
      Regression tests cover hostname resolution and failure modes.
- [x] **C10.5 (P1) gRPC proto compilation imports generated code in-process.** `tasks/call.py:100–140`
      now derives unique module names from a SHA-256 hash of the proto bytes, runs `protoc` in a
      subprocess with a 30-second timeout, and documents the trust requirement in the docstring.
      Regression tests in `tests/resources/test_grpc.py` cover unique module names and protoc
      error surfacing.
- [x] **C10.6 (P1) Script `source` can read arbitrary local files.** `tasks/run.py` now resolves
      script sources against `WORKFLOW_SCRIPT_BASE_DIR` (defaulting to the current working dir) and
      rejects any path that escapes that directory via `..` or absolute traversal.
- [x] **C10.7 (P1) Container task mounts are unrestricted.** `tasks/run.py` now defaults bind
      mode to `"ro"`, validates host paths against `WORKFLOW_CONTAINER_VOLUME_ALLOWLIST`, and rejects
      paths outside the allowed roots. Opting into `"rw"` requires a dict volume spec with
      `mode: rw`.
- [x] **C10.8 (P1) `_evaluation_budget` is a no-op on Windows.** `expressions.py` now uses a
      thread-based `TimeoutError` injection fallback on non-POSIX platforms and non-main threads,
      so JSONata expressions are bounded everywhere.
- [x] **C10.9 (P1) Unbounded agent sub-agent recursion.** `tasks/agent.py` now tracks recursion
      depth and raises `ValueError` when `WORKFLOW_MAX_SUB_AGENT_DEPTH` (default 10) is exceeded.
- [x] **C10.10 (P1) SQLiteRunHistory is not thread-safe.** `ops/history.py` now opens the SQLite
      connection with `check_same_thread=False` and protects every operation with a `threading.Lock`.
- [x] **C10.11 (P1) `WorkflowWorker.run_forever` has no error recovery.** `ops/worker.py` now
      wraps each `run_once()` call in `try/except`, logs the failure, and sleeps with exponential
      backoff capped at 60 seconds before retrying.
- [x] **C10.12 (Low) AuditLog hash-chain cannot detect deletion.** `security/audit.py` now
      includes a monotonic `index` in each entry's hashed payload and `verify()` checks that indices
      are sequential; deleting any entry (including the last) breaks verification. Regression test
      added.
- [x] **C10.13 (Low) HTTP-client redirect consistency.** `tasks/call.py` and `tasks/events.py`
      now instantiate `httpx.AsyncClient(follow_redirects=False)` explicitly everywhere for
      defense-in-depth.
- [x] **C10.14 (P1) Windows POSIX test runner command compatibility.** Replaced `printf` and
      `sleep` in `tests/core/test_run_handlers.py` and `tests/ops/test_memoization.py` with
      equivalent `sys.executable` Python one-liners.

### C11 — Dependency hygiene  *(P0/P1)*

- [x] **C11.1 (P0) `hypothesis` and `mutmut` are runtime deps.** Moved both from
      `[project.dependencies]` to `[project.optional-dependencies.dev]` in `pyproject.toml`;
      `uv.lock` regenerated.
- [x] **C11.2 (P1) Add `[project.urls]`.** Added `Repository`, `Documentation`, `Changelog`, and
      `Issues` URLs to `pyproject.toml`.
- [x] **C11.3 (P1) Verify `import openworkflow_adk` works with no optional extras.** Verified in
      a clean venv with only runtime dependencies (`uv venv` + `uv pip install -e .`); import
      succeeds without the `brokers` or `dev` extras.
- [x] **C11.4 (P2) Consider lazy broker imports.** `resources/broker.py` already imports
      `aiokafka`, `aio-pika`, and `nats-py` lazily inside instance methods, so `import
      openworkflow_adk` works without the `brokers` extra; no `__getattr__` changes needed.

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
- [x] **C12.7 (P2) `scripts/` has no index.** Added `scripts/README.md` describing
      `check_mutation_score.py` and `fetch_schema.py`.
- [x] **C12.8 (P2) Extend `.gitignore`.** Added `.tmp-test/`, `_dist-check/`, `.idea/`, `*.whl`,
      and `*.tar.gz`.
- [x] **C12.9 (P2) Document the format hook's bash requirement.** Added a note in `AGENTS.md`
      that the PostToolUse hook requires Git Bash/WSL on Windows.
- [x] **C12.10 (P2) Add a `## License` section to README + an `AUTHORS`/`AUTHORS` policy.** Added
      a `## License` section to `README.md` pointing to `LICENSE` and `CONTRIBUTING.md`.

### C13 — Test structure & public API surface  *(P2)*

- [x] **C13.1 Add `tests/tasks/` or document transitive coverage.** Created
      `tests/tasks/test_call.py` with direct unit tests for `_compile_grpc_proto` (unique hash-suffixed
      module names and protoc error surfacing). The remaining task modules continue to be covered
      via translator/integration tests.
- [x] **C13.2 Remove the empty `tests/conftest.py`** (docstring only) or add the shared fixtures it
      promises. Removed the empty `tests/conftest.py`.
- [x] **C13.3 Move `tests/eval_agent.py`** out of the tests root (breaks the `tests/<category>/`
      mirror; referenced as `tests.eval_agent` from `tests/core/test_adk_evaluation.py`). Moved to
      `tests/eval/eval_agent.py`; updated `tests/core/test_adk_evaluation.py` to reference
      `tests.eval.eval_agent`.
- [x] **C13.4 Audit `__init__.py` `__all__`.** Split the infrastructure classes listed in C13.4
      into a new provisional namespace at `openworkflow_adk.internal`. Reduced `__all__` in
      `openworkflow_adk/__init__.py` to user-facing types; existing code can still import the moved
      names from root for backward compatibility, but they are no longer advertised as stable public
      API. Updated test imports to prefer `openworkflow_adk.internal`.
- [x] **C13.5 Test or drop untested exports.** Added `tests/test_public_api.py` with importability
      tests for every name in `openworkflow_adk.__all__` and `openworkflow_adk.internal.__all__`.
      This covers previously untested exports such as `hierarchical_pattern`, `graph_to_document`,
      `OidcMetadata`, `AuditEntry`, `SimplificationResult`, and `ModelReference`.

### C14 — CI/CD: hygiene, supply chain, cost & performance  *(P0/P1)*

Current state: `.github/workflows/ci.yml` (7 jobs) + `release.yml`; **no dependabot, no CodeQL,
no caching, no concurrency, no path filters, no permissions block, no workflow linting, no timeouts.**
Action versions verified 2026-08-11 — re-verify quarterly (dependabot will help once C14.4 lands).

- [x] **C14.1 (P0) Least-privilege `permissions` on ci.yml.** Added top-level
      `permissions: contents: read` to `ci.yml`.
- [x] **C14.2 (P0) Add CodeQL for Python.** Added `.github/workflows/codeql.yml` running
      `github/codeql-action/init@v3` + `analyze@v3` on push/PR to `main` and weekly cron with
      `permissions: security-events: write`.
- [x] **C14.3 (P0) Add `actions/dependency-review-action@v5`** Added
      `.github/workflows/dependency-review.yml` on pull requests with `fail-on-severity: moderate`.
- [x] **C14.4 (P0) Add `.github/dependabot.yml`** Added `.github/dependabot.yml` with weekly
      `github-actions` and `uv` ecosystems.
- [x] **C14.5 (P1) Upgrade outdated actions.** Upgraded `actions/checkout@v4 â†’ v5` and
      `astral-sh/setup-uv@v6 â†’ v9` across `ci.yml`, `codeql.yml`, `dependency-review.yml`, and
      `release.yml`. `actions/setup-python@v5` and `pypa/gh-action-pypi-publish@release/v1` were
      already current.
- [x] **C14.6 (P1) Cancel stale runs.** Added a `concurrency` group to `ci.yml` that cancels
      in-progress runs for pull requests on the same ref.
- [x] **C14.7 (P1) Enable uv caching.** Added `enable-cache: true` and
      `cache-dependency-glob: uv.lock / pyproject.toml` to every `setup-uv` step in `ci.yml`.
- [x] **C14.8 (P1) Path filtering.** Added `paths-ignore` for `**.md`, `docs/**`, and
      `examples/**` to `ci.yml` push and pull_request triggers.
- [x] **C14.9 (P1) Pull mutation + benchmark off per-push.** Moved `benchmark` and `mutation`
      jobs to a new `.github/workflows/extended.yml` triggered nightly (`cron: 17 3 * * *`),
      `workflow_dispatch`, and release tags. Added `timeout-minutes` to every job in `ci.yml`,
      `extended.yml`, `codeql.yml`, and `dependency-review.yml`.
- [x] **C14.10 (P1) Consolidate duplicate jobs.** Removed the redundant `adk-compat` job; the
      `compatibility-matrix` job already covers the pinned ADK version across Python versions.
- [x] **C14.11 (P1) Remove redundant catalog pytest.** Removed the duplicate
      `pytest tests/resources/test_catalog.py` run from the `test` job; the prior full pytest run
      already covers it.
- [x] **C14.12 (P1) Standardize `uv sync` flags.** Changed CI test jobs to
      `uv sync --frozen --all-extras` and added `uv sync --frozen --no-dev` to `release.yml` before
      the build step. `uv.lock` remains committed.
- [x] **C14.13 (P2) DRY the setup boilerplate.** Created the composite action
      `.github/actions/setup-owf/action.yml` and replaced the repeated
      `checkout â†’ setup-uv â†’ setup-python â†’ uv sync` sequence in `ci.yml`, `extended.yml`, and
      `release.yml` with a single `uses: ./.github/actions/setup-owf` step.
- [x] **C14.14 (P2) Coverage upload + document gate.** Added `codecov/codecov-action@v5` to the
      `test` job to upload `coverage.xml`. Kept `--cov-fail-under=80` because the measured baseline
      is ~82%, so 80 provides a small margin for platform variance.
- [x] **C14.15 (P2) Lint the workflows themselves.** Added a `workflow-lint` job to `ci.yml`
      that installs `actionlint-py` and `zizmor` from PyPI and runs them against
      `.github/workflows` on every push/PR.
- [x] **C14.16 (P2) Security findings â†’ SARIF/code-scanning.** `pip-audit` does not natively emit
      SARIF, so the `workflow-lint` job now runs `zizmor --format sarif` and uploads the SARIF file
      via `github/codeql-action/upload-sarif@v3`. `anchore/sbom-action@v0` remains pinned to major
      version 0; SBOM upload to the dependency graph is left as a future enhancement.
- [x] **C14.17 (P2) `workflow_dispatch` on ci.yml.** Added `workflow_dispatch` to `ci.yml` for
      manual reruns. Parametrized the `extended.yml` benchmark job's `--iterations` and
      `--max-p99-ms` via `workflow_dispatch` inputs with defaults of 10 and 5000.

### C15 — Release workflow hardening  *(P0 — ties to C9)*

`release.yml` has never fired (no tags exist — see C9.1/C9.4). When it does, it builds + publishes
with **no tests and no artifact validation** between tag and PyPI.

- [x] **C15.1 (P0) Gate publish on tests.** Added a `test` job to `release.yml` that runs the
      suite, lint, and format checks; the `publish` job now `needs: [test, version-check]`.
- [x] **C15.2 (P0) Tag/version consistency check.** Added a `version-check` job that extracts the
      `project.version` from `pyproject.toml` and fails if it does not match the pushed tag.
- [x] **C15.3 (P1) Smoke-test the built artifact.** Added a smoke-test step in `release.yml` that
      installs the built wheel into a fresh venv and verifies `owf-adk --version` and
      `import openworkflow_adk`.
- [ ] **C15.4 (P1) Validate trusted-publishing end-to-end.** Requires PyPI-side trusted-publisher registration for this repository/workflow/environment and a live tag push. The workflow configuration is correct; actual end-to-end validation can only happen during the first release.
      live tag push; cannot be verified statically. The workflow expects the `release` GitHub
      Environment and the `pypa/gh-action-pypi-publish@release/v1` action.
- [x] **C15.5 (P1) Auto-create the GitHub Release.** Added a `release-notes` job that runs after
      successful publish and uses `softprops/action-gh-release@v2` with auto-generated notes.
- [x] **C15.6 (P2) `attestations: true` is now the default** in current
      `pypa/gh-action-pypi-publish`; removed the redundant explicit line from `release.yml`.
- [x] **C15.7 (P2) Wire CHANGELOG to release notes.** The `release-notes` job now extracts the CHANGELOG section matching the pushed tag and uses it as the GitHub Release body, falling back to auto-generated notes when no matching section exists.
      `release-please` or an auto-changelog step so `CHANGELOG.md` and the GH Release stay in sync
      with the version bump (C4.1/C4.2 in the historical record were manual).

### C16 — Best practices & architectural recommendations  *(P1/P2)*

Follow-ups from the deep-dive best practices review and codebase validation.

- [x] **C16.1 (P1) Path traversal guard for script source files.** `tasks/run.py:136–148`
      already resolves the canonical path with `Path.resolve()` and verifies it is relative to
      `WORKFLOW_SCRIPT_BASE_DIR` (defaulting to the current working directory).
- [x] **C16.2 (P1) Dynamic gRPC proto compilation isolation.** Completed under C10.5.
      `tasks/call.py:100–140` now compiles in a subprocess with a timeout and uses hash-suffixed
      module names.
- [x] **C16.3 (P1) Resilient worker error recovery loop.** Completed under C10.11.
      `ops/worker.py` now catches errors and retries with exponential backoff capped at 60 seconds.
- [x] **C16.4 (P1) Cross-platform timeout for JSONata evaluation.** Completed under C10.8.
      `expressions.py` now falls back to a thread-based timeout injection on non-POSIX platforms.
- [ ] **C16.5 (P2) Refine public API surface area in `__init__.py`.** Tracked as C13.4.
      `openworkflow_adk/__init__.py` exports 88 symbols (`__all__`). Separate internal infrastructure
      builders/transports into an internal namespace to preserve public API stability commitments.

### C17 — Flavor (extended/catalog mode) gaps  *(P0/P1)*

Findings from a focused review of the two-flavor system ([ADR 0008](docs/decisions/0008-workflow-flavors.md)).
Catalog function resolution (`with_catalog_functions`) is called in **exactly one place**
(`runtime.py:99`) — so catalog mode only works end-to-end through `owf-adk run`. Verified by direct
read 2026-08-11.

#### Implementation bugs

- [ ] **C17.1 (P0) `lint`/`plan`/`graph` never resolve catalog functions.** `with_catalog_functions`
      is invoked only inside `run_workflow` (`runtime.py:99`); `tools/diagnostics.py` has no catalog
      reference. A catalog-mode workflow whose `do:` is `[call: makeGreeting]` runs fine but
      `owf-adk plan|graph|lint` operate on a document where `makeGreeting` is unresolved â†’ incomplete
      plan/graph or a lint error. Wire catalog resolution (registry + `base_dir`) into the diagnostics
      path, or document that these commands don't support catalog mode.
- [ ] **C17.2 (P0) `--mode` exists only on `run`.** `cli.py:24` adds `--mode` to `run_parser` only;
      `lint`/`plan`/`graph`/`test` call `load(args.file)` with no mode (cli.py:37/41/44/49). Hard policy
      mode is impossible when inspecting. Add `--mode` to the other subcommands (or to the top-level
      parser).
- [ ] **C17.3 (P0) `test` command is broken for catalog mode.** `cli.py:46-60` calls
      `run_workflow(document, input)` with no `mode` AND no `catalog_base_dir` — compare `run`
      (cli.py:72-79) which passes both. A relative `functions: functions.yaml` resolves from the
      process CWD, not `examples/catalog/` â†’ wrong file or `FileNotFoundError`. `owf-adk test
      examples/catalog/greeting.yaml --fixtures â€¦` does not work.
- [x] **C17.4 (P1) Auto-detection reconciled between loader and runtime.** `runtime.py` now recursively detects agent usage and skips catalog merging in `auto` mode when an agent is present, matching the loader precedence.
      `loader.py:140-141` gates on `mode == "auto" and not has_agent and _catalog_has_functions(raw)`;
      `runtime.py:95-96` uses `mode == "auto" and any(item.functions â€¦)` with **no `not has_agent`
      check**. A document with **both** `agent:` and a `functions` catalog in `auto` mode loads as
      extended (loader) but runs with catalog functions merged (runtime) — the load-time rejection
      ("catalog mode does not allow the agent extension") never fires, silently merging the two
      flavors ADR 0008 says to keep apart. Reconcile the two paths (the loader's `not has_agent`
      precedence is the documented one) and document the agent+catalog precedence rule.

#### Documentation gaps

- [x] **C17.5 (P1) `docs/flavors.md` expanded.** Added end-to-end examples for both extended and catalog flavors and a "when to pick which" decision guide.
      example for either flavor. A user cannot learn to write a catalog-mode workflow from this page.
      Add end-to-end examples for both flavors (extended with `agent:`, catalog with `use.catalogs` +
      an external functions file) and a "when to pick which" decision guide.
- [x] **C17.6 (P1) Malformed `endpoint` removed.** Dropped the invalid `endpoint: file://./functions.yaml` from `examples/catalog/greeting.yaml`, `examples/catalog/summarize.yaml`, and `docs/reference/catalogs.md`; documented that `functions` is the operative resolver.
      done: `docs/reference/catalogs.md:10-11` shows both `endpoint: file://./functions.yaml` and
      `functions: ./functions.yaml`; `examples/catalog/greeting.yaml:9` carries
      `endpoint: file://./functions.yaml` — **`file://./` is not a valid file URI** (parses as
      host=`.`). The text says `endpoint` is vestigial but every example still ships it. Either drop
      `endpoint` from the examples or fix the URI; stop shipping a broken field users will copy.
- [x] **C17.7 (P1) Catalog examples indexed.** Added `greeting` and `summarize` to `examples/catalog.json`.
      `examples/catalog.json` lists only `hello`/`echo`/`approval`/`multi-agent`/`rag` (all extended
      mode). `greeting`/`summarize` live in `examples/catalog/` but aren't referenced. **C3.5 is
      marked `[x]` done but the gallery index does not include them** — unmark or actually add them.
- [x] **C17.8 (P2) `docs/reference/extended.md` added.** New reference doc covering `agent:`, registries, tools, and multi-agent teams.
      (catalog has a reference doc, extended doesn't). Add one covering `agent:`, tools, memory,
      teams, and the `use.models`/`use.providers`/`use.memories` registries — or fold both into a
      single `docs/reference/flavors.md` with subsections.

#### Test gaps

- [x] **C17.9 (P1) Test agent + catalog auto-mode conflict.** Added `test_auto_mode_with_agent_prefers_extended_and_skips_catalog` to verify the loader/runtime agreement.
      `tests/resources/test_catalog.py:135-140` covers only *explicit* catalog-mode rejection; the
      divergent auto-mode case (both keys present) is untested. Add a test asserting the documented
      precedence (extended wins) and that the two detection paths agree.
- [x] **C17.10 (P1) Tests for catalog-aware CLI subcommands.** Added `tests/tools/test_cli.py` tests for `lint`, `plan`, `graph`, `test`, and `run` with `--mode catalog`.
      went unnoticed by CI. Add CLI-integration tests that run each subcommand against a catalog-mode
      fixture and assert the catalog function is resolved (or document the unsupported surface and
      assert the documented error).

---

### Open questions (not yet items)

- **Q1** Is v0.2.0 meant to be a published release? If yes, C9.1 + C9.4 + C11.2 + C12.1 are blocking.
  If no (internal-only), downgrade C9/C11/C12 priority and mark the Release workflow as inert.
- **Q2** The vendored schema is OpenWorkflow v1.0.3 (per AGENTS.md). Run the `spec-drift-check` skill
  before any C10/C11 work that touches task semantics — upstream may have moved.
### C18 — Extended-flavor OpenWorkflow interoperability  *(P0)*

Focus the project on the extended flavor: OpenWorkflow v1.0.3 YAML is consumed
by this ADK translator and should also be safe for other implementors (e.g.,
SonataFlow) to parse and ignore without error. ADK-specific configuration is
added/interpreted by this translator only.

- [x] **C18.1 Audit ADK extensions against the vendored OpenWorkflow schema.**
      Audit findings:
      - Task-level: `agent`, `self_heal` violate `unevaluatedProperties: false` on
        `$defs/task` and task-kind subschemas.
      - Project-level: `use.models`, `use.providers`, `use.memories` violate
        `unevaluatedProperties: false` on `properties/use`.
      - The fields nested inside `agent` (`output_key`, `request_input`,
        `generate_content_config`, `sub_agents`, `tools`, `memory`, `provider`)
        are invalid only because their parent `agent` object is invalid; they can
        move as a group.
      - OpenWorkflow-compatible containers: `task.metadata` and
        `document.metadata` both declare `additionalProperties: true` in the
        upstream schema, so other implementors will parse and ignore ADK config
        placed there. Project registries can also live in `use.extensions`, but
        `document.metadata.adk` is simpler and does not require an extension name.
- [x] **C18.2 Design an OpenWorkflow-compatible encoding for ADK extensions.**
      Encoding:
      - Task-level ADK config moves to `task.metadata.adk` as an object with keys
        `agent`, `self_heal`, and any future ADK directives.
      - Project-level registries move to `document.metadata.adk` as
        `{models, providers, memories}`.
      - The legacy direct form (`agent:`, `self_heal:`, `use.models:`) remains
        accepted during a deprecation window and is normalized to the new encoding
        at load time.
- [x] **C18.3 Update Pydantic models to accept the new encoding.** Added
      `AdkMetadata` and `effective_*` helpers on `TaskBase` and
      `OpenWorkflowDocument`.
- [x] **C18.4 Update loader validation.** Validates the ADK payload with
      Pydantic, strips catalog `functions` URIs before upstream schema
      validation, and resolves model/provider/memory references from
      `document.metadata.adk`.
- [x] **C18.5 Update the ADK translator.** All consumers read via
      `effective_agent()`, `effective_self_heal()`, `effective_models()`,
      `effective_providers()`, and `effective_memories()`.
- [x] **C18.6 Update examples to use the interoperable encoding.** Rewrote
      `examples/multi-agent.yaml` and `examples/rag.yaml` to use
      `metadata.adk` / `document.metadata.adk`.
- [x] **C18.7 Add round-trip tests.** Added `tests/core/test_interop.py`:
      loads `metadata.adk` documents, validates against the vendored schema,
      translates, and runs end-to-end.
- [x] **C18.8 Add cross-platform parse tests.** Verified pure OpenWorkflow
      loads and `metadata.adk` documents pass upstream schema validation.
- [x] **C18.9 Update documentation.** Rewrote `docs/reference/extension-spec.md`,
      `docs/reference/extended.md`, and related docs for the `metadata.adk`
      encoding.
- [x] **C18.10 Add an export/lint helper.** Added `owf-adk export
      --format openworkflow` and `owf-adk lint --strict`. `export` strips
      `metadata.adk` and catalog `functions`; `lint --strict` rejects ADK
      extensions.
- [x] **C18.11 Remove legacy ADK-extension support.** Removed the deprecated
      direct-property forms (`agent:`, `self_heal:`, `use.models:`,
      `use.providers:`, `use.memories:`) and updated all tests and docs to the
      `metadata.adk` encoding only.

---

### C19 — Post-migration cleanup and bug fixes  *(P1)*

Follow-ups from the legacy-encoding removal audit. These close inconsistencies
and remove dead code exposed by the migration to `metadata.adk`.

#### Code fixes

- [x] **C19.1 Fix diagnostic path for missing agent instruction.**
      `tools/diagnostics.py:52` now reports `do[{index}].metadata.adk.agent.instruction`.
- [x] **C19.2 Remove redundant `AgentCharacteristics.agent` boolean.** The field
      was removed; presence of `metadata.adk.agent` is now the sole signal.
- [ ] **C19.3 Resolve/validate sub-agent model references.** Sub-agents inherit
      `AgentCharacteristics` but their `model: {use: name}` references are not
      resolved in `tasks/agent.py` or validated in `loader.py`.
- [ ] **C19.4 Make memory-service discovery recursive.**
      `runtime.memory_service_for_document` only scans top-level `document.do`;
      nested agents in `do`, `try`, `fork`, or `switch` are missed.
- [ ] **C19.5 Make state-schema derivation recursive and cover switch cases.**
      `state.py` only adds top-level agent `output_key` values; nested agents and
      switch branches are skipped.
- [ ] **C19.6 Make diagnostics recursive.** `tools/diagnostics.py` only lints
      top-level tasks; nested tasks are not checked.
- [ ] **C19.7 Scope `metadata.adk` contents by location.** Task-level
      `metadata.adk` should only allow `agent`/`self_heal`; document-level
      `metadata.adk` should only allow `models`/`providers`/`memories`. Either
      split `AdkMetadata` or add location-aware validation.
- [x] **C19.8 Add legacy-encoding rejection with a helpful error.**
      `_legacy_extension_errors` detects top-level task keys `agent`/`self_heal`
      and `use.models`/`use.providers`/`use.memories` and emits a migration hint.
- [x] **C19.9 Remove dead defaults unwrapping in `config.py`.** Removed the
      branch that unwrapped a top-level `agent:` key from defaults files.
- [ ] **C19.10 Harden metadata access in loader validators.** The chained
      `value.get("metadata", {}).get("adk", {}).get("agent")` guards assume
      `metadata` is a dict; non-dict values crash with `AttributeError`.
- [x] **C19.11 Reconcile CLI `_catalog_mode()` with loader/runtime precedence.**
      `cli.py:_catalog_mode()` now uses `_has_agent(document.do)` to mirror the
      loader/runtime agent detection.

#### Tests

- [x] **C19.20 Add rejection tests for legacy keys.** Added loader tests for
      legacy `agent:` and `use.models:` rejection with migration hints.
- [x] **C19.21 Add tests for `metadata.adk.agent: {agent: false}` behavior.**
      The inner `agent` boolean was removed; presence of `metadata.adk.agent`
      now always enables the agent.
- [ ] **C19.22 Add tests for sub-agent model reference resolution/validation.**
- [ ] **C19.23 Add tests for nested agent memory and state-schema coverage.**

---

### C20 — Documentation and schema hygiene  *(P1)*

Docs, editor integration, changelog, and public API cleanup.

- [x] **C20.1 Update VS Code snippet to emit `metadata.adk.agent`.**
      `.vscode/openworkflow.code-snippets` now emits `metadata.adk.agent`.
- [ ] **C20.2 Rewrite or remove stale JSON extension schema.**
      `docs/schema/agent-characteristics.json` describes the old direct-task
      `agent` object and is referenced by `.vscode/settings.json` and
      `docs/guides/editor-integration.md`.
- [ ] **C20.3 Update ADR 0001.** `docs/decisions/0001-agent-characteristics-key.md`
      prescribes the removed `agent:` task key; mark it superseded and describe
      `metadata.adk.agent`.
- [ ] **C20.4 Update ADR 0005.** `docs/decisions/0005-model-reference.md`
      references the removed `use.models` registry.
- [ ] **C20.5 Update ADR 0008.** `docs/decisions/0008-workflow-flavors.md`
      describes flavor selection based on the `agent:` key.
- [ ] **C20.6 Update upstream proposal.**
      `docs/proposals/0001-agent-characteristics-upstream.md` still uses the
      legacy encoding.
- [x] **C20.7 Update `.env.example` comments.** Named registries now refer to
      `document.metadata.adk.models`/`providers`/`memories`.
- [x] **C20.8 Fix incomplete sentence in configuration doc.** Fixed the dangling
      broker-backed listen sentence.
- [ ] **C20.9 Mention `metadata.adk` in `CLAUDE.md`.** The architectural baseline
      refers to per-task agent config without naming the container.
- [x] **C20.10 Add CHANGELOG entry for C18/C19.** Added an Unreleased section
      documenting the encoding break and the `metadata.adk` container.
- [ ] **C20.11 Export `AdkMetadata` or make `adk_metadata()` private.**
      `TaskBase.adk_metadata()` and `OpenWorkflowDocument.adk_metadata()` return
      `AdkMetadata`, which is not in `openworkflow_adk.__all__`.

---

### C21 — API-first agent serving  *(P1 — strategic direction)*

Shift the primary consumption model from CLI-driven workflow execution to
API-calling agents/workflows. Reuse ADK-native protocol support instead of
building custom interface layers.

- [x] **C21.1 Decide on serving stack and protocols.** HTTP/REST first via
      FastAPI + Uvicorn; A2A/MCP/OpenAPI adapters deferred to C21.5.
- [x] **C21.2 Add a `serve` CLI command or library entrypoint.** Added
      `owf-adk serve workflow.yaml --host --port` and `openworkflow_adk.server.serve()`.
- [x] **C21.3 Define request/response shape.** `POST /run` accepts JSON
      `{input, session_id, user_id}` and returns `{workflow, events}`; `POST /run/stream`
      returns collected events as an SSE stream; `GET /health` reports workflow name.
- [ ] **C21.4 Wire persistent sessions/history.** Server-mode runs use
      `run_workflow` directly, but explicit session/history backend configuration
      for long-lived server processes is not yet exposed.
- [ ] **C21.5 Add protocol-specific adapters.** A2A (workflow as ADK agent), MCP
      (workflow tasks as tools), and OpenAPI spec generation remain future work.
- [x] **C21.6 Security defaults.** Bind defaults to `127.0.0.1`; egress validation
      and secret resolution are inherited from `run_workflow`. Production TLS/auth
      still requires a reverse proxy.
- [x] **C21.7 Tests and examples.** Added `tests/tools/test_server.py` covering
      health, run, and streaming endpoints. A curl/example snippet can be added
      under `examples/` in a follow-up.
