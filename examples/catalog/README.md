# Catalog mode examples

These workflows share [`functions.yaml`](functions.yaml). They contain no
`agent:` task extension, so they can be validated and run in catalog mode:

```bash
owf-adk run examples/catalog/greeting.yaml --mode catalog
owf-adk run examples/catalog/summarize.yaml --mode catalog --input '{"text":"Hello"}'
```

`makeGreeting` demonstrates a deterministic reusable function. `summarize`
demonstrates the same catalog pattern for an LLM HTTP endpoint; configure the
endpoint and set `WORKFLOW_SECRET__OPENAI_KEY` before running it. The
`endpoint` field is retained for OpenWorkflow catalog compatibility; the
`functions` URI is the field used by this implementation to load functions.
