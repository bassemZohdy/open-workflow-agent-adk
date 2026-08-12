"""Minimal HTTP server for running OpenWorkflow documents as ADK agents."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from pydantic import BaseModel

from openworkflow_adk.loader import load
from openworkflow_adk.models import OpenWorkflowDocument
from openworkflow_adk.runtime import run_workflow


class RunRequest(BaseModel):
    input: dict[str, Any] = {}
    session_id: str | None = None
    user_id: str = "workflow-user"


def _check_deps() -> None:
    try:
        import fastapi  # noqa: F401
        import uvicorn  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "server extras are required; install with 'pip install open-workflow-agent-adk[server]'"
        ) from exc


def create_app(
    document: OpenWorkflowDocument | str,
    *,
    model_factory: Callable[[str], Any] | None = None,
    function_registry: dict[str, Callable[..., Any]] | None = None,
    workflow_registry: Any | None = None,
    event_sink: Callable[[Any], None | Awaitable[None]] | None = None,
) -> Any:
    """Return a FastAPI app that runs a loaded OpenWorkflow document."""
    _check_deps()
    from fastapi import Body, FastAPI, HTTPException
    from fastapi.responses import JSONResponse, StreamingResponse

    if isinstance(document, str):
        document = load(document)

    app = FastAPI(title=f"owf-adk: {document.document.name}")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "workflow": document.document.name}

    @app.post("/run")
    async def run(payload: RunRequest = Body(...)) -> JSONResponse:
        try:
            events = await run_workflow(
                document,
                payload.input,
                user_id=payload.user_id,
                session_id=payload.session_id or "workflow-session",
                model_factory=model_factory,
                function_registry=function_registry,
                workflow_registry=workflow_registry,
                event_sink=event_sink,
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return JSONResponse(
            content={
                "workflow": document.document.name,
                "events": [_event_to_json(event) for event in events],
            }
        )

    @app.post("/run/stream")
    async def run_stream(payload: RunRequest = Body(...)) -> StreamingResponse:
        async def generator():
            collected: list[Any] = []

            async def sink(event: Any) -> None:
                collected.append(event)

            try:
                await run_workflow(
                    document,
                    payload.input,
                    user_id=payload.user_id,
                    session_id=payload.session_id or "workflow-session",
                    model_factory=model_factory,
                    function_registry=function_registry,
                    workflow_registry=workflow_registry,
                    event_sink=sink,
                )
            except Exception as exc:
                yield f"event: error\ndata: {str(exc)}\n\n"
                return
            for event in collected:
                yield f"data: {_event_to_json(event)}\n\n"

        return StreamingResponse(generator(), media_type="text/event-stream")

    return app


def _event_to_json(event: Any) -> dict[str, Any]:
    return {
        "author": getattr(event, "author", None),
        "output": getattr(event, "output", None),
        "error": getattr(event, "error_message", None),
    }


def serve(
    document: OpenWorkflowDocument | str,
    *,
    host: str = "127.0.0.1",
    port: int = 8080,
    model_factory: Callable[[str], Any] | None = None,
    function_registry: dict[str, Callable[..., Any]] | None = None,
    workflow_registry: Any | None = None,
) -> None:
    """Start a Uvicorn server for the given workflow document."""
    _check_deps()
    import uvicorn

    app = create_app(
        document,
        model_factory=model_factory,
        function_registry=function_registry,
        workflow_registry=workflow_registry,
    )
    uvicorn.run(app, host=host, port=port)
