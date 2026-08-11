import sys
from pathlib import Path

import grpc
import pytest
import respx
from grpc_tools import protoc

from openworkflow_adk import load, run_workflow
from openworkflow_adk.tasks.call import _compile_grpc_proto

PROTO = """
syntax = \"proto3\";
service Echo {
  rpc Ping (PingRequest) returns (PingReply);
}
message PingRequest { string name = 1; }
message PingReply { string message = 1; }
"""

SERVER_PROTO = PROTO.replace("service Echo", "package server;\nservice Echo")


async def test_grpc_call_compiles_proto_and_invokes_reflected_method(tmp_path) -> None:
    proto_path = tmp_path / "echo.proto"
    proto_path.write_text(SERVER_PROTO)
    assert (
        protoc.main(
            [
                "grpc_tools.protoc",
                f"-I{tmp_path}",
                f"--python_out={tmp_path}",
                f"--grpc_python_out={tmp_path}",
                str(proto_path),
            ]
        )
        == 0
    )
    sys.path.insert(0, str(tmp_path))
    try:
        import echo_pb2

        async def ping(request, context):
            return echo_pb2.PingReply(message=f"Hello {request.name}")

        server = grpc.aio.server()
        handler = grpc.method_handlers_generic_handler(
            "Echo",
            {
                "Ping": grpc.unary_unary_rpc_method_handler(
                    ping,
                    request_deserializer=echo_pb2.PingRequest.FromString,
                    response_serializer=echo_pb2.PingReply.SerializeToString,
                )
            },
        )
        server.add_generic_rpc_handlers((handler,))
        port = server.add_insecure_port("127.0.0.1:0")
        await server.start()
        try:
            with respx.mock:
                respx.get("https://proto.test/echo.proto").respond(
                    content=PROTO.encode(), headers={"content-type": "text/plain"}
                )
                document = load(
                    {
                        "document": {
                            "dsl": "1.0.3",
                            "namespace": "demo",
                            "name": "grpc",
                            "version": "1.0.0",
                        },
                        "do": [
                            {
                                "ping": {
                                    "call": "grpc",
                                    "with": {
                                        "proto": {
                                            "endpoint": {"uri": "https://proto.test/echo.proto"}
                                        },
                                        "service": {
                                            "name": "Echo",
                                            "host": "127.0.0.1",
                                            "port": port,
                                        },
                                        "method": "Ping",
                                        "arguments": {"name": "Ada"},
                                    },
                                }
                            }
                        ],
                    }
                )
                fixture = load(Path(__file__).parents[2] / "tests" / "fixtures" / "grpc.yaml")
                fixture.do[0].task.with_.update(document.do[0].task.with_)
                document = fixture
                events = await run_workflow(document)
            assert any(event.output == {"message": "Hello Ada"} for event in events)
        finally:
            await server.stop(0)
    finally:
        sys.path.remove(str(tmp_path))


def test_compile_grpc_proto_uses_unique_hash_suffixed_modules(tmp_path) -> None:
    """Regression: each distinct proto compiles into a uniquely-named module pair."""
    proto_a = PROTO.encode()
    proto_b = PROTO.replace("Echo", "EchoTwo").replace(
        'syntax = "proto3";', 'syntax = "proto3";\npackage beta;'
    ).encode()

    sys.path.insert(0, str(tmp_path))
    try:
        mod_a, grpc_a = _compile_grpc_proto(proto_a, str(tmp_path))
        mod_b, grpc_b = _compile_grpc_proto(proto_b, str(tmp_path))

        assert mod_a.__name__ != mod_b.__name__
        assert grpc_a.__name__ != grpc_b.__name__
        assert mod_a.__name__.startswith("owf_grpc_")
        assert grpc_a.__name__.startswith("owf_grpc_")
        assert grpc_a.__name__.endswith("_pb2_grpc")
        # Same bytes produce the same module name (deterministic import).
        mod_a2, grpc_a2 = _compile_grpc_proto(proto_a, str(tmp_path))
        assert mod_a2.__name__ == mod_a.__name__
        assert grpc_a2.__name__ == grpc_a.__name__
    finally:
        sys.path.remove(str(tmp_path))


def test_compile_grpc_proto_surfaces_protoc_errors(tmp_path) -> None:
    """Invalid proto bytes must raise a descriptive ValueError."""
    with pytest.raises(ValueError, match="protoc exit"):
        _compile_grpc_proto(b"not a valid proto", str(tmp_path))
