# Task coverage

| Task/feature | Status | Notes |
|---|---|---|
| `wait`, `set`, `raise` | Supported | ADK `FunctionNode` handlers |
| `call: http` | Supported | HTTP, expressions, output modes, basic/bearer auth |
| `call: openapi` | Supported | operation lookup and basic parameter binding |
| agent extension | Supported | injected model factory enables deterministic tests |
| `switch` | Supported | routed ADK edges |
| `fork` | Supported | fan-out/join and competing race |
| `try`/`catch`, `for`, nested `do` | Supported | dynamic ADK node dispatch |
| `emit`/`listen` | Supported | in-memory broker adapter |
| `call: function` | Partial | Python registry API; document registry integration pending |
| `run: shell` | Supported | subprocess output modes |
| `run: script` | Partial | Python inline/local source; JavaScript pending |
| gRPC, AsyncAPI, A2A, MCP, containers, subflows | Deferred | handlers pending |
| durable sessions, scheduling, production deployment | Deferred | runtime hardening pending |
