"""Loading and two-stage validation for OpenWorkflow documents."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from pydantic import ValidationError

from openworkflow_adk.models import AdkMetadata, AgentCharacteristics, OpenWorkflowDocument
from openworkflow_adk.schema import load_schema_for


class WorkflowValidationError(ValueError):
    """Structured validation failure with document paths and messages."""

    def __init__(self, errors: list[dict[str, str]]) -> None:
        self.errors = errors
        message = "; ".join(f"{item['path']}: {item['message']}" for item in errors)
        super().__init__(message)


def _parse_source(source: str | Path | dict[str, Any]) -> dict[str, Any]:
    if isinstance(source, dict):
        return deepcopy(source)
    path = Path(source) if isinstance(source, Path) or "\n" not in source else None
    if path is not None and path.is_file():
        text = path.read_text()
    else:
        text = str(source)
    if (path and path.suffix.lower() == ".json") or text.lstrip().startswith(("{", "[")):
        return json.loads(text)
    import yaml

    value = yaml.safe_load(text)
    if not isinstance(value, dict):
        raise WorkflowValidationError([{"path": "$", "message": "document must be an object"}])
    return value


def _strip_agent(value: Any, parent: str | None = None) -> Any:
    if isinstance(value, dict):
        # `metadata.adk` is an OpenWorkflow-compatible container
        # (additionalProperties: true); preserve it untouched for upstream schema
        # validation while stripping legacy ADK extensions everywhere else.
        if parent == "adk":
            return {key: item for key, item in value.items()}
        return {
            key: _strip_agent(item, "catalog" if parent == "catalogs" else key)
            for key, item in value.items()
            if key not in {"agent", "self_heal"}
            and not (parent == "catalog" and key == "functions")
            and not (parent == "use" and key in {"models", "providers", "memories"})
        }
    if isinstance(value, list):
        return [_strip_agent(item, "catalog" if parent == "catalogs" else parent) for item in value]
    return value


def _model_reference_errors(value: Any, models: set[str], path: str = "$") -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    if isinstance(value, dict):
        agent = value.get("agent")
        if isinstance(agent, dict) and isinstance(agent.get("model"), dict):
            reference = agent["model"].get("use")
            if reference not in models:
                errors.append(
                    {
                        "path": f"{path}.agent.model.use",
                        "message": f"unknown model reference {reference!r}",
                    }
                )
        metadata_adk = (
            value.get("metadata", {}).get("adk", {}).get("agent") if value.get("metadata") else None
        )
        if isinstance(metadata_adk, dict) and isinstance(metadata_adk.get("model"), dict):
            reference = metadata_adk["model"].get("use")
            if reference not in models:
                errors.append(
                    {
                        "path": f"{path}.metadata.adk.agent.model.use",
                        "message": f"unknown model reference {reference!r}",
                    }
                )
        for key, item in value.items():
            errors.extend(_model_reference_errors(item, models, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            errors.extend(_model_reference_errors(item, models, f"{path}[{index}]"))
    return errors


def _registry_reference_errors(
    value: Any, providers: set[str], memories: set[str], path: str = "$"
) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    if isinstance(value, dict):
        agents: list[tuple[str, Any]] = []
        if isinstance(value.get("agent"), dict):
            agents.append((f"{path}.agent", value["agent"]))
        metadata_adk = (
            value.get("metadata", {}).get("adk", {}).get("agent") if value.get("metadata") else None
        )
        if isinstance(metadata_adk, dict):
            agents.append((f"{path}.metadata.adk.agent", metadata_adk))
        for agent_path, agent in agents:
            for field, known, label in (
                ("memory", memories, "memory"),
                ("provider", providers, "provider"),
            ):
                reference = agent.get(field)
                if isinstance(reference, dict) and reference.get("use") not in known:
                    errors.append(
                        {
                            "path": f"{agent_path}.{field}.use",
                            "message": f"unknown {label} reference {reference.get('use')!r}",
                        }
                    )
            model = agent.get("model")
            if isinstance(model, dict):
                provider = model.get("provider")
                if isinstance(provider, dict) and provider.get("use") not in providers:
                    errors.append(
                        {
                            "path": f"{agent_path}.model.provider.use",
                            "message": f"unknown provider reference {provider.get('use')!r}",
                        }
                    )
        for key, item in value.items():
            errors.extend(_registry_reference_errors(item, providers, memories, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            errors.extend(_registry_reference_errors(item, providers, memories, f"{path}[{index}]"))
    return errors


def _contains_adk_extension(value: Any, parent: str | None = None) -> bool:
    """Return True if the raw document still contains ADK-specific fields."""
    if isinstance(value, dict):
        if parent == "metadata" and "adk" in value:
            return True
        for key, item in value.items():
            if key in {"agent", "self_heal"}:
                return True
            if parent == "use" and key in {"models", "providers", "memories"}:
                return True
            if _contains_adk_extension(item, key):
                return True
        return False
    if isinstance(value, list):
        return any(_contains_adk_extension(item, parent) for item in value)
    return False


def _effective_registries(
    raw: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Return merged model/provider/memory registries.

    Legacy ``use.models``/``use.providers``/``use.memories`` are accepted
    during the deprecation window and merged with the interoperable
    ``document.metadata.adk.{models,providers,memories}`` encoding.
    The metadata encoding takes precedence on key collisions.
    """
    use = raw.get("use", {}) or {}
    adk = ((raw.get("document") or {}).get("metadata") or {}).get("adk") or {}
    return (
        {**use.get("models", {}), **(adk.get("models") or {})},
        {**use.get("providers", {}), **(adk.get("providers") or {})},
        {**use.get("memories", {}), **(adk.get("memories") or {})},
    )


def _to_pure_openworkflow(value: Any, parent: str | None = None) -> Any:
    """Return a copy with all ADK extensions removed for pure OpenWorkflow export."""
    if isinstance(value, dict):
        # Strip the ADK payload from metadata containers but keep other metadata.
        if parent == "metadata":
            return {
                key: _to_pure_openworkflow(item, key) for key, item in value.items() if key != "adk"
            }
        result: dict[str, Any] = {}
        for key, item in value.items():
            if key in {"agent", "self_heal"}:
                continue
            if parent == "use" and key in {"models", "providers", "memories"}:
                continue
            result[key] = _to_pure_openworkflow(item, key)
        return result
    if isinstance(value, list):
        return [_to_pure_openworkflow(item, parent) for item in value]
    return value


def _extension_errors(value: Any, path: str = "$") -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    if isinstance(value, dict):
        if "agent" in value:
            try:
                AgentCharacteristics.model_validate(value["agent"])
            except ValidationError as exc:
                for error in exc.errors():
                    location = ".".join(str(part) for part in error["loc"])
                    errors.append({"path": f"{path}.agent.{location}", "message": error["msg"]})
        if isinstance(value.get("metadata"), dict) and isinstance(
            value["metadata"].get("adk"), dict
        ):
            try:
                AdkMetadata.model_validate(value["metadata"]["adk"])
            except ValidationError as exc:
                for error in exc.errors():
                    location = ".".join(str(part) for part in error["loc"])
                    errors.append(
                        {"path": f"{path}.metadata.adk.{location}", "message": error["msg"]}
                    )
        for key, item in value.items():
            errors.extend(_extension_errors(item, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            errors.extend(_extension_errors(item, f"{path}[{index}]"))
    return errors


def load_raw(source: str | Path | dict[str, Any]) -> dict[str, Any]:
    """Parse YAML/JSON text, a file, or a mapping into a raw document dict."""
    return _parse_source(source)


def load(source: str | Path | dict[str, Any], *, mode: str = "auto") -> OpenWorkflowDocument:
    """Load YAML/JSON text, a file, or a mapping into a typed document."""
    if mode not in {"auto", "extended", "catalog"}:
        raise ValueError("mode must be auto, extended, or catalog")
    raw = _parse_source(source)
    has_agent = _contains_key(raw, "agent")
    catalog_mode = mode == "catalog" or (
        mode == "auto" and not has_agent and _catalog_has_functions(raw)
    )
    if catalog_mode and has_agent:
        raise WorkflowValidationError(
            [{"path": "$", "message": "catalog mode does not allow the agent extension"}]
        )
    errors = _extension_errors(raw)
    model_registry, provider_registry, memory_registry = _effective_registries(raw)
    errors.extend(_model_reference_errors(raw, set(model_registry)))
    errors.extend(_registry_reference_errors(raw, provider_registry, memory_registry))
    for source_path, source_registry in (
        ("$.use.models", raw.get("use", {}).get("models", {})),
        (
            "$.document.metadata.adk.models",
            ((raw.get("document") or {}).get("metadata") or {}).get("adk", {}).get("models", {}),
        ),
    ):
        if not isinstance(source_registry, dict):
            continue
        for model_name, model_def in source_registry.items():
            if not isinstance(model_def, dict):
                continue
            provider = model_def.get("provider")
            if isinstance(provider, dict) and provider.get("use") not in set(provider_registry):
                errors.append(
                    {
                        "path": f"{source_path}.{model_name}.provider.use",
                        "message": f"unknown provider reference {provider.get('use')!r}",
                    }
                )
    try:
        schema = load_schema_for(str(raw.get("document", {}).get("dsl", "")))
    except ValueError as exc:
        errors.append({"path": "$.document.dsl", "message": str(exc)})
        schema = None
    if schema is not None:
        errors.extend(
            {
                "path": "$"
                + "".join(
                    f"[{part!r}]" if isinstance(part, int) else f".{part}" for part in error.path
                ),
                "message": error.message,
            }
            for error in Draft202012Validator(schema).iter_errors(_strip_agent(raw))
        )
    if errors:
        raise WorkflowValidationError(errors)
    try:
        return OpenWorkflowDocument.model_validate(raw)
    except ValidationError as exc:
        raise WorkflowValidationError(
            [
                {"path": ".".join(str(part) for part in error["loc"]), "message": error["msg"]}
                for error in exc.errors()
            ]
        ) from exc


def _contains_key(value: Any, key: str) -> bool:
    if isinstance(value, dict):
        return key in value or any(_contains_key(item, key) for item in value.values())
    if isinstance(value, list):
        return any(_contains_key(item, key) for item in value)
    return False


def _catalog_has_functions(value: Any) -> bool:
    catalogs = value.get("use", {}).get("catalogs", {}) if isinstance(value, dict) else {}
    return isinstance(catalogs, dict) and any(
        isinstance(item, dict) and item.get("functions") for item in catalogs.values()
    )
