# Catalog mode reference

Catalog mode is the spec-pure flavor of OpenWorkflow ADK. A workflow references
an external functions file through the project extension below:

```yaml
use:
  catalogs:
    shared:
      functions: ./functions.yaml
do:
  - answer:
      call: summarize
      with:
        text: '${ .question }'
```

The functions file has a `functions` object whose values are ordinary
OpenWorkflow tasks:

```yaml
functions:
  summarize:
    call: http
    with:
      method: post
      endpoint: https://api.openai.com/v1/chat/completions
      body:
        model: gpt-4o-mini
        messages:
          - role: user
            content: '${ .text }'
```

The `functions` URI is the operative resolver. The `endpoint` field is
vestigial in this implementation and is ignored; remove it from new workflows.
Supported URI forms are local paths, `file://` paths, and HTTP(S) URLs. Local
relative paths are resolved from the catalog base directory supplied by the
caller. Catalog contents are cached by URI and content hash within a registry
instance, so multiple workflows can share one loaded function set.

Catalog mode rejects the agent extension (`task.metadata.adk.agent`). Use
extended mode when inline ADK agent configuration, ADK tools, memory, or agent
teams are required.
