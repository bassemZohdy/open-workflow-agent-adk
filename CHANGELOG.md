# Changelog

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
