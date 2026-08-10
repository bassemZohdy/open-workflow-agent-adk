# Security boundaries

Workflow `run: shell` and `run: script` tasks execute child processes with a
60-second default timeout (`WORKFLOW_RUN_DEFAULT_TIMEOUT`), resource limits
when configured, and a sanitized environment. Variables beginning with
`WORKFLOW_SECRET__` are never passed to those child processes.

The process sandbox is best-effort. It applies POSIX resource limits and Linux
`no-new-privileges`, but it does not create a network namespace or install a
seccomp profile. Sandboxed code can therefore still make outbound network
connections; use container or deployment-level network policy for isolation.

Catalog HTTP resources do not follow redirects. Local catalog files must be
under the workflow's catalog base directory, which prevents `file://` path
traversal. Keep catalog sources trusted and configure
`WORKFLOW_EGRESS_ALLOWLIST` for approved hosts.
