# Proposal: Agent characteristics for OpenWorkflow tasks

Status: Draft for upstream submission  
Owner: OpenWorkflow ADK maintainers  
Target baseline: OpenWorkflow DSL 1.0.x

## Summary

Add an optional `agent` extension to task objects so a workflow can declare the
model, instruction, tools, output key, memory, provider, and coordinator
members needed to execute an agent task. Existing workflows remain valid and
non-agent runtimes may ignore or reject the extension according to their
extension policy.

## Proposed shape

```yaml
do:
  - summarize:
      agent:
        model: gemini-2.5-flash
        instruction: Summarize the supplied context.
        tools: []
        output_key: summary
      set:
        source: $context.input
```

The initial schema should define `agent` as an optional object with strict
known fields. `sub_agents` is recursive and enables coordinator patterns;
`provider` and `memory` may reference named entries in `use.providers` and
`use.memories`. Implementations should preserve task-level validation for all
non-extension fields.

## Compatibility and validation

The extension is additive for the 1.0.x line. A conforming validator should
validate the base task after removing the extension key, then validate the
extension object against its own versioned schema. Unknown extension fields
must produce a source-oriented validation error. Extension versions should be
independent from the DSL version and use minor versions for additive fields.

## Runtime guidance

An implementation may map the object to its native agent runtime. It should
document model-provider configuration, state/output semantics, tool safety,
human-input suspension, and sub-agent handoff behavior. The extension must not
change the meaning of ordinary `call`, `run`, `set`, or control-flow tasks.

## Reference implementation and acceptance cases

This repository contains the reference translation, extension schema, loader
tests, provider adapters, team handoff test, human-input suspend/resume test,
and compatibility tests for additive 1.0.x patch versions. Upstream review
should confirm:

1. An ordinary 1.0.x workflow remains valid.
2. An agent task validates and executes with a configured model.
3. Unknown agent fields fail with a precise path.
4. A coordinator can hand off to a declared sub-agent.
5. The extension can evolve independently without weakening base validation.
