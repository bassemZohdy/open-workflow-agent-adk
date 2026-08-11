# Examples gallery

- `hello.yaml` — deterministic state update and container smoke-test input.
- `echo.yaml` — HTTP call against the compose echo service.
  **Prerequisite:** run `docker compose up --wait` so `http://echo:8080` resolves.
- `approval.yaml` — event-driven approval using `listen` and `switch`.
  **Prerequisite:** an external producer must emit an `approval.completed` event or the workflow
  blocks indefinitely.
- `rag.yaml` — retrieval HTTP call followed by an agent task.
  **Prerequisite:** the example uses the non-routable host `retriever.example`; replace the
  endpoint with a real retrieval service before running.
- `multi-agent.yaml` — two sequential agent tasks (draft, then review).
- `catalog/` — two spec-pure workflows sharing deterministic and LLM-wrapping functions.
