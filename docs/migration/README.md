# Runtime consolidation: preparation only

This repository has not been migrated or archived. The following gates must
be satisfied before replacing an installed runtime or retiring its source.

## Standalone distribution gates

The original baseline is `48db0cf5e1a1d3202cbbec6021736e1d89e94cd0`.
The standalone Apache-2.0 distribution `open-workflow-agent-adk` v0.2.1 provides
namespace `openworkflow_adk` and CLIs `owf-adk` / `spec-drift-check`.
The canonical MIT [ADK engine manifest](https://github.com/bassemZohdy/open-workflow-agent/blob/15bcfba17b4327f927d0729c03c968718738f6db/engines/adk/pyproject.toml)
declares the same distribution name v0.2.0 but namespace `open_workflow_agent_adk`.
Installing a higher version does not imply API/import compatibility.

Before changing a name, release coordinate or supported import, choose whether
to keep a distinctly named compatibility package preserving `openworkflow_adk`
and its CLIs, or perform an explicitly breaking retirement of those APIs.
The canonical runtime remains the migration target in either case; it must have
one unambiguous owner for each published package/image coordinate.

| Standalone surface retained at origin | Required target decision / proof |
|---|---|
| `owf-adk` CLI and `openworkflow_adk` Python API | Command/flags/import compatibility or documented breaking replacement |
| `document.metadata.adk` named registries and `task.metadata.adk.agent` | Translate defaults/registries/per-task/environment precedence into ordinary OWA resources; no proprietary public DSL |
| JSONata expressions and workflow extension modes | Deliberate conversion to canonical jq/portable profile with unsupported syntax rejected; parsing alone is insufficient |
| Native ADK tasks, tools, self-heal and persistence | Adapter/service ownership, retry/side-effect/replay and storage fixtures |
| Protocol/ops modules, suspension, replay and scheduling | Consumer contract, storage and optional-adapter disposition, rather than inferred equivalence |
| Examples, tests, branch/PR changes and local stash | Unique-content reconciliation and explicit branch/PR disposition before archive |

Keep the original [Apache-2.0 license](../../LICENSE) and origin notices with
any later port; nothing is relabeled under the canonical repository's MIT file.
Current source code and license contents are unchanged by this stage.

[Lock/canary repair PR15](https://github.com/bassemZohdy/open-workflow-agent-adk/pull/15)
is separate and remains draft: its Dependency Review cannot complete while
the repository's dependency graph is unsupported/disabled. This proposal does
not alter that setting, dependency-review workflow, package name, runtime schema
or credential. The other existing PRs/refs and local stash remain preserved.

There is no independently safe retirement yet. The smallest product choice is
compatibility-package support versus breaking CLI/import retirement; even after
that choice, fixture/consumer and source-license gates must be completed.

## Target and compatibility boundary

Workflow behavior belongs in [Open Workflow Agent at the reviewed baseline](https://github.com/bassemZohdy/open-workflow-agent/tree/15bcfba17b4327f927d0729c03c968718738f6db).
Its public authoring contract is Open Workflow 1.0.3; core is framework neutral.
Managed definitions/catalog/deployment lifecycle belong in
[Open Simple Agent at the reviewed baseline](https://github.com/bassemZohdy/open-simple-agent/tree/178039de5b4060d9a7a8b593fcbb479ee57eecb7)
only where a missing management capability has been established. The current
inspection found no direct predecessor SDK import in those two canonical source
trees. This is not an inventory of external installations.

The mappings below are a migration plan, not tested drop-in compatibility.
No legacy configuration loader, provider credential, database, deployment,
package name or live client is changed by this documentation stage.

## Repository-side preparation

The accompanying [source manifest](source-manifest.json) records every tracked
file at the original revision, with its Git blob id, mode and disposition.
Original source, histories, branches, tags and unpublished local refs remain
preserved. Complete-history Git bundles were independently restored, compared
ref-for-ref and checked with `git fsck --full` during preparation. No LFS
objects were found. These Git backups do not include ignored live settings or
untracked runtime data; those existing files were left untouched.

There is no runtime code or configuration copied into a canonical repository
in this stage. License files and provenance remain unchanged. A manifest entry
marked pending is not evidence that its behavior has been migrated.

## Acceptance and rollback

1. Identify callers by package/import, image digest, service/Live URL, auth
   contract, session/checkpoint store and custom tool/function modules.
   The bounded portfolio source scan found only self references and the
   canonical ADK distribution's own references; it cannot prove no external users.
2. Reconcile each selected fixture on both advertised engines, using deterministic
   models and isolated temporary stores. Preserve model/role/tool differences,
   output shapes, cancellation, timeouts, retry budgets and runtime error codes.
3. For approval, prove pending/unknown/rejected/expired states cannot execute an
   action, approved decisions are operator-bound, and restart/replay cannot
   duplicate the action. A status string or prompt is not approval enforcement.
4. Keep credentials/auth settings and live storage untouched until a separately
   reviewed consumer cutover. Verify migration and rollback with the chosen
   deployment before changing an installed client or service.
5. Before read-only archival, complete unique-file dispositions, preserve all
   current refs/collaboration, resolve licensing/package ownership and publish
   accurate consumer instructions. No archive is authorized by an incomplete
   checklist. Archive only after those gates pass; permanent deletion is excluded.

Reverting this documentation commit restores the previous documentation without
changing executable behavior. Original commits remain addressable. Future live
cutover must retain the original immutable image/package and database snapshot;
record how to reconcile writes after cutover rather than assuming an old backup
alone can recover them.

Existing OWA [portable fixture tests](https://github.com/bassemZohdy/open-workflow-agent/blob/15bcfba17b4327f927d0729c03c968718738f6db/tests/contract/test_contract.py)
and [durable approval replay test](https://github.com/bassemZohdy/open-workflow-agent/blob/15bcfba17b4327f927d0729c03c968718738f6db/tests/contract/test_durable_approvals.py)
are a target baseline. They are not migration acceptance for this predecessor.
