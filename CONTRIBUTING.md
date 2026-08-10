# Contributing

## Workflow

1. Open an issue or RFC for behavior that changes the DSL, runtime contracts,
   security model, or persistence format.
2. Keep changes focused and add an acceptance test for each TODO item.
3. Run `uv run ruff check .`, `uv run ruff format --check .`, and
   `uv run pytest -q` before submitting a pull request.
4. Maintainers triage issues weekly; security reports should use private
   disclosure and are acknowledged within five business days.

## Decision records

Architecture changes belong in `docs/decisions/` with status, alternatives,
trade-offs, migration impact, and a rollback plan. Breaking changes require a
release-note entry and an explicit compatibility decision.
