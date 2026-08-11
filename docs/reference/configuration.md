# Configuration reference

Agent values use three layers, with later entries overriding earlier ones:

```text
project defaults < task.metadata.adk.agent < environment
```

Environment variables use the `WORKFLOW_` prefix and `__` for nesting:

```text
WORKFLOW_AGENT__MODEL=gemini-2.5-flash
WORKFLOW_AGENT__GENERATE_CONTENT_CONFIG__temperature=0.2
```

Boolean, numeric, null, and JSON object/array values are decoded when possible.
Defaults may be supplied as a mapping or YAML/JSON file to
`resolve_agent_characteristics`.

The CLI supports dotenv-style files with `--env`; values are loaded into the
process environment before the document is translated.

Named model providers live in `document.metadata.adk.providers`:

```yaml
document:
  metadata:
    adk:
      providers:
        openai-prod:
          type: openai
          base_url: https://api.openai.com/v1
          credential: openai-key
use:
  secrets: [openai-key]
```

The corresponding deployment overrides are
`WORKFLOW_PROVIDERS__OPENAI-PROD__BASE_URL` and
`WORKFLOW_PROVIDERS__OPENAI-PROD__CREDENTIAL`. Credentials resolve from
`WORKFLOW_SECRET__<name>` and are never taken from inline provider values.
OpenAI-compatible adapters currently cover OpenAI, Azure, Ollama, and vLLM;
Gemini and Anthropic continue through ADK's native model resolution.

Semantic memory uses the same named-registry pattern under
`document.metadata.adk.memories`:

```yaml
document:
  metadata:
    adk:
      memories:
        local:
          type: file
          connection: .workflow-memory.json
```

`agent.memory: {use: local}` selects the ADK memory service for the run. The
available backends are `in-memory`, `file`, `redis`, `postgres`, and `vertex`.
Redis/Postgres round-trip tests run through the opt-in Testcontainers suite;
Vertex additionally requires ADK's GCP extra and an agent engine ID.
File, Redis, Postgres, and Vertex services can be reused across run instances;
completed ADK sessions are added to the configured memory service after a run,
and the agent's `load_memory` tool can recall matching prior context.

Multimodal agent input can be passed through with
`run_workflow(..., message=google.genai.types.Content(...))`; image and audio
parts are forwarded unchanged to ADK.

Callers that need incremental delivery can provide `event_sink`; it is invoked
for every ADK event as it arrives and may be synchronous or asynchronous. The
existing return value remains the complete event list.

Set `token_budget` on `run_workflow` to enforce a run-level usage ceiling from
ADK `total_token_count` metadata. Agent tasks continue to select models and
providers independently through their `metadata.adk.agent.model`/`provider` configuration.
Session/state persistence is a separate concern and uses ADK's `InMemory`,
database, or Vertex session services configured through
`WORKFLOW_SESSION_BACKEND`.

Runtime sessions use `InMemorySessionService` by default. Set
`WORKFLOW_SESSION_BACKEND=vertex` for `VertexAiSessionService`, with
`GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, and optionally
`WORKFLOW_VERTEX_AGENT_ENGINE_ID` supplied by the deployment environment.
For a self-hosted durable backend, use `WORKFLOW_SESSION_BACKEND=sqlite` and
set `WORKFLOW_SESSION_DATABASE_URL` to a SQLAlchemy async database URL (for
example, `sqlite+aiosqlite:///workflow-sessions.db`).

Run-history checkpoints default to every emitted event. Set
`WORKFLOW_CHECKPOINT_INTERVAL=0` to disable intermediate writes, or pass
`checkpoint_interval` to `run_workflow`; the selected history backend remains
the checkpoint backend.

For a process restart, call `run_workflow(..., resume=True)` with the same
SQLite history and session identifiers. The runtime resumes after the last
successfully checkpointed top-level task and reuses its persisted state.

When a persistent history backend is supplied, timer waits can be suspended
instead of keeping a task alive. `run_workflow` records `status: suspended`,
the wait task, and `resume_at`; a later `resume=True` call continues after the
timer. The threshold defaults to one hour and can be changed with
`WORKFLOW_SUSPEND_WAIT_SECONDS` or the `suspend_after` argument.
With persistent history, broker-backed `listen` tasks also suspend without
holding a consumer task. The matching event is consumed when the run is
resumed, so the broker must retain it between suspension and resume.

Agent tasks can request external approval/input with
`metadata.adk.agent.request_input: {question: ...}`. The runtime records a `human_input`
suspension and resumes it with `resume=True` plus `resume_input=<value>`.
