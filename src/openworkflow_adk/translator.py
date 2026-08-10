"""Initial OpenWorkflow-to-ADK translation spine."""

from __future__ import annotations

import asyncio
import importlib
import inspect
import json
import os
import re
import shlex
import shutil
import signal
import sys
import tempfile
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
import yaml
from google.adk.agents import LlmAgent
from google.adk.workflow import Workflow
from google.adk.workflow._function_node import FunctionNode
from google.adk.workflow._graph import DEFAULT_ROUTE
from google.adk.workflow._join_node import JoinNode

from openworkflow_adk.security.auth import resolve_authentication
from openworkflow_adk.resources.broker import Broker
from openworkflow_adk.config import resolve_agent_characteristics, resolve_provider_config
from openworkflow_adk.errors import OpenWorkflowError
from openworkflow_adk.expressions import bind, evaluate
from openworkflow_adk.models import TASK_KEYS, OpenWorkflowDocument, ProviderConfig, Task, TaskItem
from openworkflow_adk.resources.providers import create_llm
from openworkflow_adk.tools.registry import WorkflowRegistry
from openworkflow_adk.ops.schedule import duration_seconds
from openworkflow_adk.security.security import validate_egress
from openworkflow_adk.state import derive_state_schema
from openworkflow_adk.ops.suspension import WorkflowSuspended

NodeBuilder = Callable[[str, Task], Any]


def _sandbox_preexec(limits: dict[str, Any] | None) -> None:
    """Apply best-effort POSIX limits in a child before executing user code."""
    if os.name != "posix":
        return
    import resource

    try:
        os.setsid()
    except PermissionError:
        # Some hardened/containerized hosts disallow creating a new session;
        # resource limits still apply and timeout cleanup falls back to the
        # child process itself on such hosts.
        pass
    limits = limits or {}
    values = (
        ("cpu_seconds", resource.RLIMIT_CPU),
        ("memory_bytes", resource.RLIMIT_AS),
        ("nofile", resource.RLIMIT_NOFILE),
    )
    for key, resource_kind in values:
        value = limits.get(key)
        if value is not None:
            amount = int(value)
            resource.setrlimit(resource_kind, (amount, amount))
    if sys.platform.startswith("linux"):
        import ctypes

        ctypes.CDLL(None).prctl(38, 1, 0, 0, 0)


def _kill_process_tree(proc: asyncio.subprocess.Process) -> None:
    if os.name == "posix":
        try:
            os.killpg(proc.pid, signal.SIGKILL)
            return
        except (PermissionError, ProcessLookupError):
            proc.kill()
            return
    proc.kill()


def _adk_name(name: str) -> str:
    value = re.sub(r"\W", "_", name)
    return value if value and not value[0].isdigit() else f"workflow_{value}"


async def _noop(ctx: Any) -> None:
    return None


def _generic_builder(name: str, _task: Task) -> FunctionNode:
    return FunctionNode(func=_noop, name=name)


def _wait_builder(
    name: str, task: Task, *, suspend_long_waits: bool = False, suspend_after: float = 3600
) -> FunctionNode:
    async def wait(ctx: Any) -> None:
        if isinstance(task.wait, dict):
            seconds = float(task.wait.get("seconds", 0))
            seconds += float(task.wait.get("minutes", 0)) * 60
            seconds += float(task.wait.get("hours", 0)) * 3600
            seconds += float(task.wait.get("milliseconds", 0)) / 1000
            if suspend_long_waits and seconds >= suspend_after:
                raise WorkflowSuspended(
                    task=name,
                    resume_at=datetime.now(timezone.utc) + timedelta(seconds=seconds),
                )
            await asyncio.sleep(seconds)

    return FunctionNode(func=wait, name=name)


def _raise_builder(name: str, task: Task) -> FunctionNode:
    async def raise_error(ctx: Any) -> None:
        error = (task.raise_ or {}).get("error", task.raise_ or {})
        if not isinstance(error, dict):
            error = {"detail": str(error)}
        raise OpenWorkflowError(
            type=str(error.get("type", "about:blank")),
            status=error.get("status"),
            title=error.get("title"),
            detail=error.get("detail"),
            instance=error.get("instance"),
        )

    return FunctionNode(func=raise_error, name=name)


def _http_builder(
    name: str,
    task: Task,
    policies: dict[str, Any] | None = None,
    environ: dict[str, str] | None = None,
) -> FunctionNode:
    async def request(ctx: Any) -> Any:
        state = ctx.state.to_dict()
        arguments = bind(task.with_ or {}, state)
        endpoint = arguments.get("endpoint")
        endpoint_auth = endpoint.get("authentication") if isinstance(endpoint, dict) else None
        if isinstance(endpoint, dict):
            endpoint = endpoint.get("uri")
        if not endpoint:
            raise ValueError(f"HTTP task {name!r} requires with.endpoint")
        validate_egress(endpoint, environ)
        method = str(arguments.get("method", "get")).upper()
        output = arguments.get("output", "content")
        follow_redirects = bool(arguments.get("redirect", False))
        auth, auth_headers = resolve_authentication(endpoint_auth, policies, environ)
        headers = dict(arguments.get("headers") or {})
        headers.update(auth_headers)
        async with httpx.AsyncClient(follow_redirects=follow_redirects) as client:
            response = await client.request(
                method,
                endpoint,
                headers=headers,
                params=arguments.get("query"),
                json=arguments.get("body"),
                auth=auth,
            )
            if 300 <= response.status_code < 400 and not follow_redirects:
                response.raise_for_status()
            response.raise_for_status()
            if output == "raw":
                return response.content
            if output == "response":
                return {
                    "status": response.status_code,
                    "headers": dict(response.headers),
                    "body": _response_content(response),
                }
            return _response_content(response)

    return FunctionNode(func=request, name=name)


def _response_content(response: httpx.Response) -> Any:
    if not response.content:
        return None
    content_type = response.headers.get("content-type", "")
    if "json" in content_type:
        return response.json()
    return response.text


def _set_builder(name: str, task: Task) -> FunctionNode:
    async def set_values(ctx: Any, node_input: Any = None) -> None:
        if isinstance(task.set, dict):
            state = ctx.state.to_dict()
            if isinstance(node_input, dict):
                state.update(node_input)
            for key, value in task.set.items():
                ctx.state[key] = evaluate(value, state)
                state[key] = ctx.state[key]

    return FunctionNode(func=set_values, name=name)


def _emit_builder(name: str, task: Task, broker: Broker | None) -> FunctionNode:
    async def emit(ctx: Any) -> None:
        if broker is None:
            return
        event = ((task.emit or {}).get("event") or {}).get("with", {})
        await broker.publish(bind(event, ctx.state.to_dict()))

    return FunctionNode(func=emit, name=name)


def _listen_builder(
    name: str, task: Task, broker: Broker | None, *, suspend_listens: bool = False
) -> FunctionNode:
    async def listen(ctx: Any) -> Any:
        if broker is None:
            return None
        configuration = (task.listen or {}).get("to", {})
        read_mode = (task.listen or {}).get("read", "data")
        filters: list[dict[str, Any]] = []
        strategy = "one"
        if isinstance(configuration, dict):
            if "one" in configuration:
                filters = [configuration["one"]]
            elif "any" in configuration:
                strategy, filters = "any", configuration["any"]
            elif "all" in configuration:
                strategy, filters = "all", configuration["all"]
        types_to_match = {
            (item.get("with") or {}).get("type") for item in filters if isinstance(item, dict)
        }
        if suspend_listens:
            raise WorkflowSuspended(
                task=name,
                resume_at=datetime.now(timezone.utc),
                reason="broker_listen",
            )

        async def next_event() -> dict[str, Any]:
            while True:
                event = await broker.consume()
                if not types_to_match or event.get("type") in types_to_match:
                    return event

        if strategy == "all":
            events = [await next_event() for _ in filters]
            result: Any = events
        else:
            result = await next_event()
        if read_mode == "data":
            if isinstance(result, list):
                return [event.get("data") for event in result]
            return result.get("data")
        return result

    return FunctionNode(func=listen, name=name)


def _switch_builder(name: str, task: Task) -> FunctionNode:
    async def route(ctx: Any) -> None:
        state = ctx.state.to_dict()
        default = DEFAULT_ROUTE
        for case in task.switch or []:
            if not isinstance(case, dict):
                continue
            case_name, configuration = next(iter(case.items()))
            if case_name == "default":
                default = case_name
            elif isinstance(configuration, dict) and evaluate(configuration.get("when"), state):
                ctx.route = case_name
                return
        ctx.route = default

    return FunctionNode(func=route, name=name)


def _compete_builder(name: str, branches: list[Any]) -> FunctionNode:
    async def compete(ctx: Any) -> Any:
        tasks = {
            asyncio.create_task(ctx.run_node(branch, use_sub_branch=True)) for branch in branches
        }
        if not tasks:
            return None
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for pending_task in pending:
            pending_task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
        winner = next(iter(done))
        return winner.result()

    return _dynamic(FunctionNode(func=compete, name=name))


def _dynamic(node: Any) -> Any:
    """Mark a node safe for ADK dynamic execution via `ctx.run_node`."""
    if hasattr(node, "rerun_on_resume"):
        node.rerun_on_resume = True
    return node


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
        proc = await asyncio.create_subprocess_exec(
            *command,
            stdin=asyncio.subprocess.PIPE if process.get("stdin") is not None else None,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, **(process.get("environment") or {})},
            preexec_fn=_sandbox_preexec(process.get("limits")) if os.name == "posix" else None,
        )
        stdin = process.get("stdin")
        timeout = None
        if isinstance(task.timeout, dict) and task.timeout.get("after") is not None:
            timeout = duration_seconds(task.timeout["after"])
        elif isinstance(task.timeout, str):
            timeout = duration_seconds(task.timeout)
        communicate = proc.communicate(str(stdin).encode() if stdin is not None else None)
        try:
            if timeout:
                stdout, stderr = await asyncio.wait_for(communicate, float(timeout))
            else:
                stdout, stderr = await communicate
        except asyncio.TimeoutError as error:
            _kill_process_tree(proc)
            await proc.wait()
            raise TimeoutError(f"run task {name!r} exceeded its timeout") from error
        values = {"stdout": stdout.decode(), "stderr": stderr.decode(), "code": proc.returncode}
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


def _function_builder(
    name: str,
    task: Task,
    functions: dict[str, Callable[..., Any]],
    function_tasks: dict[str, Task] | None = None,
    registry: NodeBuilderRegistry | None = None,
) -> FunctionNode:
    function = functions.get(task.call or "")
    reusable = (function_tasks or {}).get(task.call or "")
    if function is None and (reusable is None or registry is None):
        raise KeyError(f"function {task.call!r} is not registered")

    async def call_function(ctx: Any) -> Any:
        arguments = bind(task.with_ or {}, ctx.state.to_dict())
        cache = registry.memoization if registry is not None else None

        async def compute() -> Any:
            if function is None and reusable is not None and registry is not None:
                node = _dynamic(registry.build(f"{name}__function", reusable))
                return await ctx.run_node(node, node_input=arguments)
            result = function(**arguments)
            return await result if inspect.isawaitable(result) else result

        if cache is not None:
            return await cache.get_or_compute(cache.key(task.call or name, arguments), compute)
        return await compute()

    return _dynamic(FunctionNode(func=call_function, name=name))


async def _read_resource(resource: Any) -> dict[str, Any]:
    source = resource
    if isinstance(source, dict):
        source = source.get("uri") or source.get("endpoint")
        if isinstance(source, dict):
            source = source.get("uri")
    if not isinstance(source, str):
        raise ValueError("OpenAPI document requires a URI or local path")
    if source.startswith(("http://", "https://")):
        validate_egress(source)
        async with httpx.AsyncClient() as client:
            response = await client.get(source)
            response.raise_for_status()
            return response.json()
    path = Path(source)
    text = path.read_text()
    return json.loads(text) if path.suffix.lower() == ".json" else yaml.safe_load(text)


async def _read_resource_bytes(resource: Any) -> bytes:
    source = resource
    if isinstance(source, dict):
        source = source.get("uri") or source.get("endpoint")
        if isinstance(source, dict):
            source = source.get("uri")
    if not isinstance(source, str):
        raise ValueError("protocol resource requires an endpoint URI or local path")
    if source.startswith(("http://", "https://")):
        validate_egress(source)
        async with httpx.AsyncClient() as client:
            response = await client.get(source)
            response.raise_for_status()
            return response.content
    return Path(source).read_bytes()


def _grpc_message_class(descriptor: Any) -> Any:
    from google.protobuf.message_factory import GetMessageClass

    return GetMessageClass(descriptor)


def _compile_grpc_proto(proto: bytes, temporary_directory: str) -> tuple[Any, Any]:
    from grpc_tools import protoc

    path = Path(temporary_directory) / "workflow_call.proto"
    path.write_bytes(proto)
    result = protoc.main(
        [
            "grpc_tools.protoc",
            f"-I{temporary_directory}",
            f"--python_out={temporary_directory}",
            f"--grpc_python_out={temporary_directory}",
            str(path),
        ]
    )
    if result != 0:
        raise ValueError(f"could not compile gRPC proto resource (protoc exit {result})")
    importlib.invalidate_caches()
    return (
        importlib.import_module("workflow_call_pb2"),
        importlib.import_module("workflow_call_pb2_grpc"),
    )


def _grpc_builder(name: str, task: Task) -> FunctionNode:
    async def call_grpc(ctx: Any) -> Any:
        import grpc
        from google.protobuf.json_format import MessageToDict, ParseDict

        arguments = bind(task.with_ or {}, ctx.state.to_dict())
        service = arguments.get("service") or {}
        service_name = service.get("name")
        method_name = arguments.get("method")
        if not service_name or not method_name:
            raise ValueError("gRPC call requires service.name and method")
        proto = await _read_resource_bytes(arguments.get("proto"))
        with tempfile.TemporaryDirectory(prefix="owf-grpc-") as directory:
            sys.path.insert(0, directory)
            try:
                proto_module, service_module = _compile_grpc_proto(proto, directory)
                descriptor = proto_module.DESCRIPTOR.services_by_name.get(service_name)
                if descriptor is None:
                    raise KeyError(f"gRPC service {service_name!r} was not found")
                method = descriptor.methods_by_name.get(method_name)
                if method is None:
                    raise KeyError(f"gRPC method {method_name!r} was not found")
                request_class = _grpc_message_class(method.input_type)
                request = ParseDict(arguments.get("arguments") or {}, request_class())
                host = service.get("host")
                port = service.get("port", 443)
                channel = grpc.aio.insecure_channel(f"{host}:{port}")
                try:
                    stub_class = getattr(service_module, f"{service_name}Stub")
                    response = await getattr(stub_class(channel), method_name)(request)
                finally:
                    await channel.close()
                return MessageToDict(response, preserving_proto_field_name=True)
            finally:
                sys.path.remove(directory)

    return _dynamic(FunctionNode(func=call_grpc, name=name))


def _openapi_builder(name: str, task: Task) -> FunctionNode:
    async def call_openapi(ctx: Any) -> Any:
        arguments = bind(task.with_ or {}, ctx.state.to_dict())
        document = await _read_resource(arguments.get("document"))
        operation_id = arguments.get("operationId")
        operation = None
        path_template = None
        for path, path_item in document.get("paths", {}).items():
            for method, candidate in path_item.items():
                if isinstance(candidate, dict) and candidate.get("operationId") == operation_id:
                    operation = (method.upper(), candidate)
                    path_template = path
                    break
            if operation:
                break
        if operation is None:
            raise KeyError(f"OpenAPI operationId {operation_id!r} was not found")
        method, operation_spec = operation
        values = arguments.get("parameters", {})
        endpoint = (document.get("servers") or [{"url": ""}])[0].get("url", "") + path_template
        query: dict[str, Any] = {}
        headers: dict[str, str] = {}
        path_parameters = (
            document.get("paths", {}).get(path_template, {}).get("parameters", []) or []
        )
        operation_parameters = operation_spec.get("parameters", []) or []
        for parameter in [*path_parameters, *operation_parameters]:
            parameter_name = parameter.get("name")
            if parameter_name not in values:
                continue
            value = values[parameter_name]
            location = parameter.get("in")
            if location == "path":
                endpoint = endpoint.replace("{" + parameter_name + "}", str(value))
            elif location == "query":
                query[parameter_name] = value
            elif location == "header":
                headers[parameter_name] = str(value)
        body = values if operation_spec.get("requestBody") else None
        async with httpx.AsyncClient(
            follow_redirects=bool(arguments.get("redirect", False))
        ) as client:
            response = await client.request(
                method, endpoint, params=query, headers=headers, json=body
            )
            response.raise_for_status()
            output = arguments.get("output", "content")
            if output == "raw":
                return response.content
            if output == "response":
                return {
                    "status": response.status_code,
                    "headers": dict(response.headers),
                    "body": _response_content(response),
                }
            return _response_content(response)

    return FunctionNode(func=call_openapi, name=name)


def _asyncapi_builder(name: str, task: Task, broker: Broker | None) -> FunctionNode:
    async def call_asyncapi(ctx: Any) -> Any:
        if broker is None:
            raise ValueError("AsyncAPI calls require a broker adapter")
        arguments = bind(task.with_ or {}, ctx.state.to_dict())
        document = await _read_resource(arguments.get("document"))
        channel = arguments.get("channel")
        operation = arguments.get("operation")
        if not channel and operation:
            for candidate_channel, item in (document.get("channels") or {}).items():
                if isinstance(item, dict) and operation in item:
                    channel = candidate_channel
                    break
            for operation_name, item in (document.get("operations") or {}).items():
                if operation_name == operation and isinstance(item, dict):
                    action = item.get("action") or item.get("channel")
                    channel = action if isinstance(action, str) else channel
        if not channel:
            raise ValueError(f"AsyncAPI task {name!r} requires a channel or operation")
        message = arguments.get("message")
        if message is not None:
            if not isinstance(message, dict):
                raise ValueError("AsyncAPI message must be an object")
            await broker.publish(
                {
                    "channel": channel,
                    "data": message.get("payload"),
                    "headers": message.get("headers", {}),
                }
            )
            return message.get("payload")
        subscription = arguments.get("subscription") or {}
        filter_expression = subscription.get("filter") if isinstance(subscription, dict) else None
        while True:
            event = await broker.consume()
            if event.get("channel") != channel:
                continue
            if filter_expression and not evaluate(
                filter_expression, {**ctx.state.to_dict(), "event": event}
            ):
                continue
            return event.get("data")

    return _dynamic(FunctionNode(func=call_asyncapi, name=name))


def _endpoint_uri(endpoint: Any) -> str | None:
    if isinstance(endpoint, str):
        return endpoint
    if isinstance(endpoint, dict):
        return endpoint.get("uri")
    return None


def _a2a_builder(name: str, task: Task) -> FunctionNode:
    async def call_a2a(ctx: Any) -> Any:
        arguments = bind(task.with_ or {}, ctx.state.to_dict())
        server = _endpoint_uri(arguments.get("server"))
        if not server and arguments.get("agentCard"):
            card = await _read_resource(arguments["agentCard"])
            server = card.get("url") or card.get("supportedInterfaces", [{}])[0].get("url")
        if not server:
            raise ValueError(f"A2A task {name!r} requires with.server or with.agentCard")
        validate_egress(server)
        method = arguments.get("method", "message/send")
        request = {
            "jsonrpc": "2.0",
            "id": name,
            "method": method,
            "params": arguments.get("parameters", {}),
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(server, json=request)
            response.raise_for_status()
            result = response.json()
        if "error" in result:
            raise OpenWorkflowError(detail=str(result["error"]), title="A2A request failed")
        return result.get("result")

    return _dynamic(FunctionNode(func=call_a2a, name=name))


async def _mcp_stdio_call(process: dict[str, Any], request: dict[str, Any]) -> Any:
    command = [process["command"], *(process.get("arguments") or [])]
    proc = await asyncio.create_subprocess_exec(
        *command,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env={**os.environ, **(process.get("environment") or {})},
    )
    assert proc.stdin is not None and proc.stdout is not None
    proc.stdin.write((json.dumps(request) + "\n").encode())
    await proc.stdin.drain()
    line = await proc.stdout.readline()
    proc.stdin.close()
    await proc.wait()
    if not line:
        raise RuntimeError("MCP stdio server returned no JSON-RPC response")
    return json.loads(line)


def _mcp_builder(name: str, task: Task) -> FunctionNode:
    async def call_mcp(ctx: Any) -> Any:
        arguments = bind(task.with_ or {}, ctx.state.to_dict())
        transport = arguments.get("transport") or {}
        method = arguments.get("method")
        if not method:
            raise ValueError(f"MCP task {name!r} requires with.method")
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": arguments.get("parameters", {}),
        }
        if "http" in transport:
            configuration = transport["http"]
            endpoint = _endpoint_uri(configuration.get("endpoint"))
            if not endpoint:
                raise ValueError("MCP HTTP transport requires endpoint.uri")
            validate_egress(endpoint)
            headers = dict(configuration.get("headers") or {})
            async with httpx.AsyncClient() as client:
                initialized = await client.post(
                    endpoint,
                    headers=headers,
                    json={
                        "jsonrpc": "2.0",
                        "id": "initialize",
                        "method": "initialize",
                        "params": {"protocolVersion": arguments.get("protocolVersion")},
                    },
                )
                initialized.raise_for_status()
                response = await client.post(endpoint, headers=headers, json=request)
                response.raise_for_status()
                result = response.json()
        elif "stdio" in transport:
            initialized = await _mcp_stdio_call(
                transport["stdio"],
                {
                    "jsonrpc": "2.0",
                    "id": "initialize",
                    "method": "initialize",
                    "params": {"protocolVersion": arguments.get("protocolVersion")},
                },
            )
            del initialized
            result = await _mcp_stdio_call(transport["stdio"], request)
        else:
            raise ValueError("MCP transport must define http or stdio")
        if "error" in result:
            raise OpenWorkflowError(detail=str(result["error"]), title="MCP request failed")
        return result.get("result")

    return _dynamic(FunctionNode(func=call_mcp, name=name))


def _run_nested_builder(
    name: str, children: list[TaskItem], registry: NodeBuilderRegistry
) -> FunctionNode:
    child_nodes = [_dynamic(registry.build(item.name, item.task)) for item in children]

    async def run_nested(ctx: Any, node_input: Any = None) -> Any:
        result = None
        for child in child_nodes:
            result = await ctx.run_node(child, node_input=node_input)
        return result

    return _dynamic(FunctionNode(func=run_nested, name=name))


def _try_builder(name: str, task: Task, registry: NodeBuilderRegistry) -> FunctionNode:
    try_node = _run_nested_builder(name, task.try_ or [], registry)
    _dynamic(try_node)
    catch = getattr(task, "catch", None)
    catch_children = []
    if isinstance(catch, dict):
        catch_children = [TaskItem.model_validate(item) for item in catch.get("do", [])]
    catch_node = _run_nested_builder(f"{name}__catch", catch_children, registry)
    _dynamic(catch_node)

    async def run_try(ctx: Any) -> Any:
        policy = task.self_heal
        max_attempts = int(policy.get("max_attempts", 1)) if isinstance(policy, dict) else 1
        for attempt in range(max(1, max_attempts)):
            try:
                return await ctx.run_node(try_node)
            except Exception as error:
                healer = registry.self_healer
                if healer is not None and attempt + 1 < max_attempts:
                    diagnosis = healer(error, ctx.state.to_dict())
                    if inspect.isawaitable(diagnosis):
                        diagnosis = await diagnosis
                    if isinstance(diagnosis, dict) and diagnosis.get("retry"):
                        patch = diagnosis.get("state")
                        if isinstance(patch, dict):
                            ctx.state.update(patch)
                        continue
                if not catch_children:
                    raise
                as_name = catch.get("as") if isinstance(catch, dict) else None
                if as_name:
                    ctx.state[as_name] = OpenWorkflowError.from_exception(error).as_dict()
                return await ctx.run_node(catch_node)

    return _dynamic(FunctionNode(func=run_try, name=name))


def _for_builder(name: str, task: Task, registry: NodeBuilderRegistry) -> FunctionNode:
    children = task.do or []
    child_nodes = [_dynamic(registry.build(item.name, item.task)) for item in children]
    configuration = task.for_ or {}
    each_name = configuration.get("each", "item")
    index_name = configuration.get("at")
    collection_expression = configuration.get("in", "[]")
    while_expression = getattr(task, "while", None)

    async def run_for(ctx: Any) -> list[Any]:
        state = ctx.state.to_dict()
        collection = evaluate(collection_expression, state)
        results = []
        for index, item in enumerate(collection or []):
            if while_expression and not evaluate(while_expression, ctx.state.to_dict()):
                break
            ctx.state[each_name] = item
            ctx.session.state[each_name] = item
            if index_name:
                ctx.state[index_name] = index
                ctx.session.state[index_name] = index
            result = None
            for child in child_nodes:
                loop_input = {each_name: item}
                if index_name:
                    loop_input[index_name] = index
                result = await ctx.run_node(child, node_input=loop_input)
            results.append(result)
        return results

    return _dynamic(FunctionNode(func=run_for, name=name))


def _agent_builder(
    name: str,
    task: Task,
    model_factory: Callable[[str], Any] | None = None,
    model_specs: dict[str, Any] | None = None,
    environ: dict[str, str] | None = None,
    tool_registry: dict[str, Callable[..., Any]] | None = None,
    provider_configs: dict[str, ProviderConfig] | None = None,
    provider_factory: Callable[[str, ProviderConfig], Any] | None = None,
    resume_input: Any = None,
    route_options: set[str] | None = None,
) -> LlmAgent:
    if task.agent is None:
        raise ValueError("agent builder requires task.agent")
    config = resolve_agent_characteristics(
        task.agent, models=model_specs, environ=environ, providers=provider_configs
    )
    return _build_agent(
        name,
        config,
        model_factory=model_factory,
        model_specs=model_specs,
        environ=environ,
        tool_registry=tool_registry,
        provider_configs=provider_configs,
        provider_factory=provider_factory,
        as_sub_agent=False,
        resume_input=resume_input,
        route_options=route_options,
    )


def _build_agent(
    name: str,
    config: Any,
    *,
    model_factory: Callable[[str], Any] | None,
    model_specs: dict[str, Any] | None,
    environ: dict[str, str] | None,
    tool_registry: dict[str, Callable[..., Any]] | None,
    provider_configs: dict[str, ProviderConfig] | None,
    provider_factory: Callable[[str, ProviderConfig], Any] | None,
    as_sub_agent: bool,
    resume_input: Any = None,
    route_options: set[str] | None = None,
) -> LlmAgent:
    """Build one ADK agent and recursively assemble its coordinator tree."""
    model = model_factory(config.model or "") if model_factory else config.model or ""
    if config.provider:
        provider = resolve_provider_config(
            config.provider.model_dump(), providers=provider_configs, environ=environ
        )
        model = (
            provider_factory(config.model or "", provider)
            if provider_factory
            else create_llm(config.model or "", provider)
        )
    tools = [
        (tool_registry or {}).get(tool, tool) if isinstance(tool, str) else tool
        for tool in config.tools
    ]
    if config.request_input is not None:
        question = str(config.request_input.get("question", "Input required to continue."))

        async def request_input(_question: str = question) -> Any:
            """Pause this agent until an external user supplies the requested input."""
            if resume_input is None:
                raise WorkflowSuspended(
                    task=name,
                    resume_at=datetime.now(timezone.utc),
                    reason="human_input",
                )
            return resume_input

        request_input.__name__ = "request_input"
        request_input.__doc__ = question
        tools.append(request_input)
    if route_options:

        async def route_to(route: str, tool_context: Any) -> str:
            """Select one of the workflow switch routes."""
            if route not in route_options:
                raise ValueError(f"unknown workflow route {route!r}")
            tool_context.state["workflow:route"] = route
            return f"selected route {route}"

        route_to.__name__ = "route_to"
        tools.append(route_to)
    if config.memory:
        from google.adk.tools import load_memory

        if load_memory not in tools:
            tools.append(load_memory)
    sub_agents = [
        _build_agent(
            child.name or f"{name}_sub_{index}",
            child,
            model_factory=model_factory,
            model_specs=model_specs,
            environ=environ,
            tool_registry=tool_registry,
            provider_configs=provider_configs,
            provider_factory=provider_factory,
            as_sub_agent=True,
            resume_input=resume_input,
            route_options=None,
        )
        for index, child in enumerate(config.sub_agents)
    ]
    return LlmAgent(
        name=name,
        description=config.description or "",
        model=model,
        instruction=config.instruction or "",
        tools=tools,
        sub_agents=sub_agents,
        generate_content_config=config.generate_content_config,
        mode="chat" if sub_agents or as_sub_agent else "single_turn",
        output_key=(config.output_key or name) if not as_sub_agent else config.output_key,
    )


class NodeBuilderRegistry:
    """Dispatch task kinds to ADK node builders."""

    def __init__(
        self,
        state_schema: type | None = None,
        broker: Broker | None = None,
        auth_policies: dict[str, Any] | None = None,
        environ: dict[str, str] | None = None,
        model_factory: Callable[[str], Any] | None = None,
        function_registry: dict[str, Callable[..., Any]] | None = None,
        function_tasks: dict[str, Task] | None = None,
        model_specs: dict[str, Any] | None = None,
        workflow_registry: WorkflowRegistry | None = None,
        provider_configs: dict[str, ProviderConfig] | None = None,
        provider_factory: Callable[[str, ProviderConfig], Any] | None = None,
        suspend_long_waits: bool = False,
        suspend_after: float = 3600,
        resume_input: Any = None,
        suspend_listens: bool = False,
        memoization: Any = None,
        self_healer: Callable[[Exception, dict[str, Any]], Any] | None = None,
    ) -> None:
        self.state_schema = state_schema
        self.broker = broker
        self.auth_policies = auth_policies or {}
        self.environ = environ
        self.model_factory = model_factory
        self.function_registry = function_registry or {}
        self.function_tasks = function_tasks or {}
        self.model_specs = model_specs or {}
        self.workflow_registry = workflow_registry
        self.provider_configs = provider_configs or {}
        self.provider_factory = provider_factory
        self.suspend_long_waits = suspend_long_waits
        self.suspend_after = suspend_after
        self.resume_input = resume_input
        self.suspend_listens = suspend_listens
        self.memoization = memoization
        self.self_healer = self_healer
        self._call_builders: dict[str, NodeBuilder] = {}
        self._builders: dict[str, NodeBuilder] = {key: _generic_builder for key in TASK_KEYS}
        self._builders.update(
            {
                "wait": lambda name, task: _wait_builder(
                    name,
                    task,
                    suspend_long_waits=self.suspend_long_waits,
                    suspend_after=self.suspend_after,
                ),
                "raise": _raise_builder,
                "set": _set_builder,
                "switch": _switch_builder,
                "call:http": _http_builder,
            }
        )

    def register(self, task_kind: str, builder: NodeBuilder) -> None:
        if task_kind not in TASK_KEYS:
            raise KeyError(f"unknown OpenWorkflow task kind: {task_kind}")
        self._builders[task_kind] = builder

    def register_call(self, scheme: str, builder: NodeBuilder) -> None:
        """Register a plugin builder for an extension ``call`` scheme."""
        if not scheme or scheme in {"http", "openapi", "grpc", "asyncapi", "a2a", "mcp"}:
            raise ValueError(f"call scheme is reserved or empty: {scheme!r}")
        self._call_builders[scheme] = builder

    def build(self, name: str, task: Task) -> Any:
        if task.agent is not None and task.agent.agent:
            agent = _agent_builder(
                name,
                task,
                self.model_factory,
                self.model_specs,
                self.environ,
                self.function_registry,
                self.provider_configs,
                self.provider_factory,
                self.resume_input,
                {
                    case_name
                    for case in task.switch or []
                    for case_name in case
                    if case_name != "default"
                }
                if task.switch
                else None,
            )
            if task.switch:

                async def routed(ctx: Any) -> Any:
                    result = await ctx.run_node(agent)
                    selected = ctx.state.to_dict().get("workflow:route")
                    ctx.route = selected or DEFAULT_ROUTE
                    return result

                return _dynamic(FunctionNode(func=routed, name=name))
            return agent
        kind = task_kind(task)
        key = f"call:{task.call}" if kind == "call" and task.call == "http" else kind
        plugin_builder = self._call_builders.get(task.call or "") if kind == "call" else None
        if kind == "do":
            node = _run_nested_builder(name, task.do or [], self)
        elif kind == "try":
            node = _try_builder(name, task, self)
        elif kind == "for":
            node = _for_builder(name, task, self)
        elif kind == "run":
            node = _run_builder(name, task, self)
        elif plugin_builder is not None:
            node = plugin_builder(name, task)
        elif kind == "call" and task.call not in {
            "http",
            "openapi",
            "grpc",
            "asyncapi",
            "a2a",
            "mcp",
        }:
            node = _function_builder(name, task, self.function_registry, self.function_tasks, self)
        elif kind == "call" and task.call == "openapi":
            node = _openapi_builder(name, task)
        elif kind == "call" and task.call == "grpc":
            node = _grpc_builder(name, task)
        elif kind == "call" and task.call == "asyncapi":
            node = _asyncapi_builder(name, task, self.broker)
        elif kind == "call" and task.call == "a2a":
            node = _a2a_builder(name, task)
        elif kind == "call" and task.call == "mcp":
            node = _mcp_builder(name, task)
        elif kind == "emit":
            node = _emit_builder(name, task, self.broker)
        elif kind == "listen":
            node = _listen_builder(name, task, self.broker, suspend_listens=self.suspend_listens)
        elif key == "call:http":
            node = _http_builder(name, task, self.auth_policies, self.environ)
        else:
            node = self._builders[key](name, task)
        if isinstance(node, FunctionNode) and self.state_schema is not None:
            node.state_schema = self.state_schema
        return node

    def keys(self) -> tuple[str, ...]:
        return tuple(self._builders)


def task_kind(task: Task) -> str:
    """Return the single schema task discriminator."""
    for key in TASK_KEYS:
        if key == "do" and task.for_ is not None:
            continue
        attribute = key if key not in {"for", "raise", "try"} else f"{key}_"
        if getattr(task, attribute) is not None:
            return key
    raise ValueError("task has no task kind")


def build_workflow(
    document: OpenWorkflowDocument,
    registry: NodeBuilderRegistry | None = None,
    broker: Broker | None = None,
    model_factory: Callable[[str], Any] | None = None,
    function_registry: dict[str, Callable[..., Any]] | None = None,
    workflow_registry: WorkflowRegistry | None = None,
    provider_configs: dict[str, ProviderConfig] | None = None,
    provider_factory: Callable[[str, ProviderConfig], Any] | None = None,
    suspend_long_waits: bool = False,
    suspend_after: float = 3600,
    resume_input: Any = None,
    suspend_listens: bool = False,
    memoization: Any = None,
    self_healer: Callable[[Exception, dict[str, Any]], Any] | None = None,
) -> Workflow:
    """Build a linear ADK Workflow from a top-level `do` task list."""
    state_schema = derive_state_schema(document)
    registry = registry or NodeBuilderRegistry(
        state_schema,
        broker,
        auth_policies=document.use.authentications,
        model_factory=model_factory,
        function_registry=function_registry,
        function_tasks={
            function_name: Task.model_validate(function_task)
            for function_name, function_task in document.use.functions.items()
        },
        model_specs=document.use.models,
        workflow_registry=workflow_registry,
        provider_configs=provider_configs or document.use.providers,
        provider_factory=provider_factory,
        suspend_long_waits=suspend_long_waits,
        suspend_after=suspend_after,
        resume_input=resume_input,
        suspend_listens=suspend_listens,
        memoization=memoization,
        self_healer=self_healer,
    )
    items: list[TaskItem] = document.do
    nodes = {item.name: registry.build(item.name, item.task) for item in items}
    fork_parts: dict[str, tuple[list[Any], JoinNode]] = {}
    for item in items:
        if task_kind(item.task) != "fork" or not isinstance(item.task.fork, dict):
            continue
        branches = []
        for branch in item.task.fork.get("branches", []):
            branch_item = TaskItem.model_validate(branch)
            branch_node = _dynamic(registry.build(branch_item.name, branch_item.task))
            nodes[branch_item.name] = branch_node
            branches.append(branch_node)
        if item.task.fork.get("compete"):
            nodes[item.name] = _compete_builder(item.name, branches)
            nodes[item.name].state_schema = state_schema
        elif branches:
            fork_parts[item.name] = (branches, JoinNode(name=f"{item.name}__join"))
    edges: list[tuple[Any, ...]] = []
    if items:
        edges.append(("START", nodes[items[0].name]))
    by_name = {item.name: index for index, item in enumerate(items)}
    pending = [0] if items else []
    visited: set[int] = set()
    while pending:
        index = pending.pop(0)
        if index in visited:
            continue
        visited.add(index)
        item = items[index]
        if task_kind(item.task) == "fork" and item.name in fork_parts:
            branches, join = fork_parts[item.name]
            edges.append((nodes[item.name], tuple(branches)))
            for branch in branches:
                edges.append((branch, join))
            continue_target = None
            if item.task.then not in {None, "continue", "end", "exit"}:
                continue_target = item.task.then
            elif index + 1 < len(items):
                continue_target = items[index + 1].name
                pending.append(index + 1)
            if continue_target:
                if continue_target not in nodes:
                    raise ValueError(
                        f"task {item.name!r} references unknown task {continue_target!r}"
                    )
                edges.append((join, nodes[continue_target]))
                pending.append(by_name[continue_target])
            continue
        if task_kind(item.task) == "switch":
            routes: dict[str, Any] = {}
            for case in item.task.switch or []:
                if not isinstance(case, dict):
                    continue
                case_name, configuration = next(iter(case.items()))
                target_name = configuration.get("then") if isinstance(configuration, dict) else None
                if target_name in nodes:
                    route_name = DEFAULT_ROUTE if case_name == "default" else case_name
                    routes[route_name] = nodes[target_name]
                    pending.append(by_name[target_name])
            if routes:
                edges.append((nodes[item.name], routes))
            continue
        directive = item.task.then
        if directive in {"end", "exit"}:
            continue
        if directive and directive not in {"continue"}:
            if directive not in nodes:
                raise ValueError(f"task {item.name!r} references unknown task {directive!r}")
            target = nodes[directive]
            pending.append(by_name[directive])
        elif index + 1 < len(items):
            target = nodes[items[index + 1].name]
            pending.append(index + 1)
        else:
            continue
        edges.append((nodes[item.name], target))
    return Workflow(name=_adk_name(document.document.name), state_schema=state_schema, edges=edges)
