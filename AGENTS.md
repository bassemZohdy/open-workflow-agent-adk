# AGENTS.md

Guidance for AI coding agents. `CLAUDE.md` holds the architectural baseline
(spec version, ADK mapping, config-layering precedence, stack) — read it first;
this file only adds what it doesn't already cover.

## Status: greenfield

No Python source, tests, Dockerfile, or CI exist yet. Only `CLAUDE.md`,
`pyproject.toml`, `.gitignore`, and the `.claude/` (hook + skill) config are
tracked. Expect to establish package layout, entrypoints, and test infra
rather than find them.

## Python is auto-formatted on every edit

`.claude/settings.json` wires a PostToolUse hook that runs
`uvx ruff format` + `uvx ruff check --fix` on every `.py` Write/Edit.
- Don't hand-format; the hook rewrites the file behind your edit.
- Re-read a file after editing if you need its final shape.
- Hook errors are swallowed (`|| true`) — ruff findings that can't be
  autofixed won't surface unless you run `uvx ruff check` yourself.

Ruff config (`pyproject.toml`): line-length 100, target py310, rules `E,F,I,UP`.

## Tooling

`uv`/`uvx` is the expected runner (the format hook depends on it). The only
declared dependency is `google-adk` (Python >=3.10); no lockfile yet.

## Before extending the OpenWorkflow schema

Run the `spec-drift-check` skill first — the project intentionally diverges
from upstream (baseline v1.0.3), so verify upstream hasn't moved before adding
task or agent-characteristics semantics.
