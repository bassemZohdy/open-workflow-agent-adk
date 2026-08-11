"""Builders for shell, script, container, and nested workflow tasks."""

from __future__ import annotations

import asyncio
import os
import shlex
import shutil
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from google.adk.workflow._function_node import FunctionNode

from openworkflow_adk.expressions import bind
from openworkflow_adk.models import Task
from openworkflow_adk.ops.schedule import duration_seconds

from .common import _kill_process_tree, _sandbox_preexec
from .simple import _dynamic

if TYPE_CHECKING:
    from openworkflow_adk.translator import NodeBuilderRegistry


def _run_workflow_builder(name: str, task: Task, registry: NodeBuilderRegistry) -> FunctionNode:
    configuration = task.run or {}
    reference = configuration.get("workflow")
    if not isinstance(reference, dict):
        raise ValueError(f"workflow task {name!r} requires a workflow reference")
    if registry.workflow_registry is None:
        raise ValueError("run: workflow requires a workflow registry")
    target = registry.workflow_registry.resolve(
        reference.get("namespace", ""),
        reference.get("name", ""),
        reference.get("version", "latest"),
    )
    from openworkflow_adk.translator import build_workflow

    nested = build_workflow(
        target,
        broker=registry.broker,
        model_factory=registry.model_factory,
        function_registry=registry.function_registry,
        workflow_registry=registry.workflow_registry,
    )

    async def run_workflow_node(ctx: Any) -> Any:
        inputs = bind(reference.get("input", {}), ctx.state.to_dict())
        return await ctx.run_node(nested, node_input=inputs)

    return _dynamic(FunctionNode(func=run_workflow_node, name=name))


def _container_builder(name: str, task: Task) -> FunctionNode:
    async def run_container(ctx: Any) -> Any:
        import docker

        configuration = bind(task.run or {}, ctx.state.to_dict())
        process = configuration.get("container")
        if not isinstance(process, dict) or not process.get("image"):
            raise ValueError(f"container task {name!r} requires container.image")
        client = docker.from_env()
        image = process["image"]
        pull_policy = process.get("pullPolicy", "ifNotPresent")
        if pull_policy == "always":
            client.images.pull(image)
        elif pull_policy == "ifNotPresent":
            try:
                client.images.get(image)
            except docker.errors.ImageNotFound:
                client.images.pull(image)
        elif pull_policy != "never":
            raise ValueError(f"unsupported container pull policy: {pull_policy!r}")

        command = process.get("command")
        arguments = list(process.get("arguments") or [])
        if command:
            command = [*shlex.split(command), *arguments]
        elif arguments:
            command = arguments
        volumes = {
            host: {"bind": target, "mode": "rw"}
            for host, target in (process.get("volumes") or {}).items()
        }
        client_ports = {
            container_port: host_port
            for container_port, host_port in (process.get("ports") or {}).items()
        }
        container = client.containers.run(
            image,
            command=command,
            name=process.get("name"),
            environment=process.get("environment") or {},
            volumes=volumes,
            ports=client_ports,
            stdin_open=process.get("stdin") is not None,
            detach=True,
            remove=False,
        )
        try:
            if process.get("stdin") is not None:
                container.attach_socket(params={"stdin": 1, "stream": 1})._sock.send(
                    str(process["stdin"]).encode()
                )
            status = container.wait()
            stdout = container.logs(stdout=True, stderr=False).decode()
            stderr = container.logs(stdout=False, stderr=True).decode()
        finally:
            container.remove(force=True)
            client.close()
        values = {"stdout": stdout, "stderr": stderr, "code": status.get("StatusCode", 1)}
        return (
            None
            if configuration.get("return", "stdout") == "none"
            else (
                values
                if configuration.get("return", "stdout") == "all"
                else values[configuration.get("return", "stdout")]
            )
        )

    return _dynamic(FunctionNode(func=run_container, name=name))


def _run_builder(
    name: str, task: Task, registry: NodeBuilderRegistry | None = None
) -> FunctionNode:
    if "workflow" in (task.run or {}):
        if registry is None:
            raise ValueError("run: workflow requires a workflow registry")
        return _run_workflow_builder(name, task, registry)
    if "container" in (task.run or {}):
        return _container_builder(name, task)

    async def run_process_uncached(ctx: Any) -> Any:
        configuration = bind(task.run or {}, ctx.state.to_dict())
        return_type = configuration.get("return", "stdout")
        if "shell" in configuration:
            process = configuration["shell"]
            command = [process["command"], *process.get("arguments", [])]
        elif "script" in configuration:
            process = configuration["script"]
            language = process.get("language", "python").lower()
            code = process.get("code")
            if code is None:
                source = process.get("source")
                source = source.get("uri") if isinstance(source, dict) else source
                if not source or not str(source).startswith(("/", ".")):
                    raise ValueError("script source must be a local path")
                code = Path(source).read_text()
            if language in {"python", "py"}:
                command = [sys.executable, "-c", code, *process.get("arguments", [])]
            elif language in {"javascript", "js", "node"}:
                node = shutil.which("node")
                if node is None:
                    raise RuntimeError("JavaScript scripts require the node executable")
                command = [node, "-e", code, *process.get("arguments", [])]
            else:
                raise NotImplementedError(f"unsupported script language: {language}")
        else:
            raise NotImplementedError("run handler supports shell and Python script")
        default_timeout = float(os.environ.get("WORKFLOW_RUN_DEFAULT_TIMEOUT", "60"))
        if default_timeout <= 0:
            raise ValueError("WORKFLOW_RUN_DEFAULT_TIMEOUT must be greater than zero")
        child_environment = {
            key: value
            for key, value in {**os.environ, **(process.get("environment") or {})}.items()
            if not key.startswith("WORKFLOW_SECRET__")
        }
        proc = await asyncio.create_subprocess_exec(
            *command,
            stdin=asyncio.subprocess.PIPE if process.get("stdin") is not None else None,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=child_environment,
            preexec_fn=_sandbox_preexec(process.get("limits")) if os.name == "posix" else None,
        )
        stdin = process.get("stdin")
        timeout = default_timeout
        if isinstance(task.timeout, dict) and task.timeout.get("after") is not None:
            timeout = duration_seconds(task.timeout["after"])
        elif isinstance(task.timeout, str):
            timeout = duration_seconds(task.timeout)
        communicate = proc.communicate(str(stdin).encode() if stdin is not None else None)
        try:
            stdout, stderr = await asyncio.wait_for(communicate, float(timeout))
        except asyncio.TimeoutError as error:
            _kill_process_tree(proc)
            await proc.wait()
            raise TimeoutError(f"run task {name!r} exceeded its timeout") from error
        values = {
            "stdout": stdout.decode().replace("\r\n", "\n"),
            "stderr": stderr.decode().replace("\r\n", "\n"),
            "code": proc.returncode,
        }
        if return_type == "none":
            return None
        if return_type == "all":
            return values
        return values[return_type]

    async def run_process(ctx: Any) -> Any:
        if registry is None or registry.memoization is None:
            return await run_process_uncached(ctx)
        arguments = bind(task.run or {}, ctx.state.to_dict())
        cache = registry.memoization
        return await cache.get_or_compute(
            cache.key(f"run:{name}", arguments), lambda: run_process_uncached(ctx)
        )

    return FunctionNode(func=run_process, name=name)
