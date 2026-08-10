# ADR 0001: Task-level agent characteristics

- Status: Accepted
- Date: 2026-08-10

## Decision

Agent characteristics are represented by a dedicated `agent` key on a task:

```yaml
do:
  - summarize:
      agent:
        model: gemini-2.5-flash
        instruction: Summarize the input.
      call: function
      with:
        name: summarize_input
```

The extension is intentionally accepted alongside the OpenWorkflow v1.0.3 task
shape. The upstream schema is still authoritative for every non-extension
field; validation removes `agent` before applying that schema and validates the
extension with this project’s Pydantic model.

## Rationale

The task is the unit translated into an ADK agent, so colocating model,
instruction, tools, and generation settings keeps workflow intent discoverable.
It also avoids requiring a separately named extension object for the common
case. `use.extensions` remains available for future cross-cutting extensions.

## Consequences

Documents using `agent` are not accepted by an unextended OpenWorkflow v1.0.3
runtime. This project must keep the extension schema and the upstream schema
versioned together and must report the divergence clearly in validation errors.
