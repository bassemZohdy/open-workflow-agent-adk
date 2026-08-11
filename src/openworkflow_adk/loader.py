"""Loading and two-stage validation for OpenWorkflow documents."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from pydantic import ValidationError

from openworkflow_adk.models import AdkMetadata, OpenWorkflowDocument
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


def _adk_agent_present(value: Any) -> bool:
    """Return True when any task carries ``metadata.adk.agent``."""
    if isinstance(value, dict):
        metadata = value.get("metadata")
        if isinstance(metadata, dict) and isinstance(metadata.get("adk"), dict):
            if isinstance(metadata["adk"].get("agent"), dict):
                return True
        return any(_adk_agent_present(item) for item in value.values())
    if isinstance(value, list):
        return any(_adk_agent_present(item) for item in value)
    return False


def _model_reference_errors(value: Any, models: set[str], path: str = "$") -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    if isinstance(value, dict):
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
        metadata_adk = (
            value.get("metadata", {}).get("adk", {}).get("agent") if value.get("metadata") else None
        )
        if isinstance(metadata_adk, dict):
            for field, known, label in (
                ("memory", memories, "memory"),
                ("provider", providers, "provider"),
            ):
                reference = metadata_adk.get(field)
                if isinstance(reference, dict) and reference.get("use") not in known:
                    errors.append(
                        {
                            "path": f"{path}.metadata.adk.agent.{field}.use",
                            "message": f"unknown {label} reference {reference.get('use')!r}",
                        }
                    )
            model = metadata_adk.get("model")
            if isinstance(model, dict):
                provider = model.get("provider")
                if isinstance(provider, dict) and provider.get("use") not in providers:
                    errors.append(
                        {
                            "path": f"{path}.metadata.adk.agent.model.provider.use",
                            "message": f"unknown provider reference {provider.get('use')!r}",
                        }
                    )
        for key, item in value.items():
            errors.extend(_registry_reference_errors(item, providers, memories, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            errors.extend(_registry_reference_errors(item, providers, memories, f"{path}[{index}]"))
    return errors


def _contains_adk_extension(value: Any) -> bool:
    """Return True if the raw document contains ADK-specific metadata."""
    if isinstance(value, dict):
        if isinstance(value.get("metadata"), dict) and "adk" in value["metadata"]:
            return True
        return any(_contains_adk_extension(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_adk_extension(item) for item in value)
    return False


def _registries(raw: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Return model/provider/memory registries from ``document.metadata.adk``."""
    adk = ((raw.get("document") or {}).get("metadata") or {}).get("adk") or {}
    return (
        adk.get("models") or {},
        adk.get("providers") or {},
        adk.get("memories") or {},
    )


def _strip_catalog_functions(value: Any, parent: str | None = None) -> Any:
    """Return a copy with catalog ``functions`` URIs stripped.

    The vendored OpenWorkflow schema allows only ``endpoint`` under
    ``use.catalogs.<name>``; ``functions`` is an ADK catalog-mode extension.
    """
    if isinstance(value, dict):
        return {
            key: _strip_catalog_functions(item, "catalog" if parent == "catalogs" else key)
            for key, item in value.items()
            if not (parent == "catalog" and key == "functions")
        }
    if isinstance(value, list):
        return [_strip_catalog_functions(item, parent) for item in value]
    return value


def _to_pure_openworkflow(value: Any, parent: str | None = None) -> Any:
    """Return a copy with ADK metadata and catalog extensions stripped."""

    if isinstance(value, dict):
        if parent == "metadata":
            return {
                key: _to_pure_openworkflow(item, key) for key, item in value.items() if key != "adk"
            }
        return {
            key: _to_pure_openworkflow(item, "catalog" if parent == "catalogs" else key)
            for key, item in value.items()
            if not (parent == "catalog" and key == "functions")
        }
    if isinstance(value, list):
        return [_to_pure_openworkflow(item, parent) for item in value]
    return value


def _legacy_extension_errors(value: Any, path: str = "$") -> list[dict[str, str]]:
    """Detect removed legacy ADK-extension keys and emit clear migration errors.

    The new encoding places ADK config inside ``metadata.adk``; this function
    ignores keys under that container so it does not flag valid new-form
    documents.
    """
    errors: list[dict[str, str]] = []
    if isinstance(value, dict):
        if path.endswith(".metadata.adk") or path.endswith("metadata.adk"):
            return errors
        for key in ("agent", "self_heal"):
            if key in value and path.startswith("$.do"):
                errors.append(
                    {
                        "path": f"{path}.{key}",
                        "message": (
                            f"legacy '{key}' task extension removed; "
                            f"move it to task.metadata.adk.{key}"
                        ),
                    }
                )
        if path == "$.use":
            for key in ("models", "providers", "memories"):
                if key in value:
                    errors.append(
                        {
                            "path": f"{path}.{key}",
                            "message": (
                                f"legacy 'use.{key}' registry removed; "
                                f"move it to document.metadata.adk.{key}"
                            ),
                        }
                    )
        for key, item in value.items():
            child_path = f"{path}.{key}"
            if path == "$" and key == "do" and isinstance(item, list):
                for index, child in enumerate(item):
                    task_path = f"{path}.do[{index}]"
                    errors.extend(_legacy_extension_errors(child, task_path))
                    if isinstance(child, dict):
                        for task_name, task in child.items():
                            errors.extend(
                                _legacy_extension_errors(task, f"{task_path}.{task_name}")
                            )
            else:
                errors.extend(_legacy_extension_errors(item, child_path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            errors.extend(_legacy_extension_errors(item, f"{path}[{index}]"))
    return errors


def _extension_errors(value: Any, path: str = "$") -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    if isinstance(value, dict):
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
    errors = _legacy_extension_errors(raw)
    has_agent = _adk_agent_present(raw)
    catalog_mode = mode == "catalog" or (
        mode == "auto" and not has_agent and _catalog_has_functions(raw)
    )
    if catalog_mode and has_agent:
        raise WorkflowValidationError(
            [{"path": "$", "message": "catalog mode does not allow the agent extension"}]
        )
    errors.extend(_extension_errors(raw))
    model_registry, provider_registry, memory_registry = _registries(raw)
    errors.extend(_model_reference_errors(raw, set(model_registry)))
    errors.extend(_registry_reference_errors(raw, provider_registry, memory_registry))
    for model_name, model_def in model_registry.items():
        if not isinstance(model_def, dict):
            continue
        provider = model_def.get("provider")
        if isinstance(provider, dict) and provider.get("use") not in set(provider_registry):
            errors.append(
                {
                    "path": f"$.document.metadata.adk.models.{model_name}.provider.use",
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
            for error in Draft202012Validator(schema).iter_errors(_strip_catalog_functions(raw))
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


def _catalog_has_functions(value: Any) -> bool:
    catalogs = value.get("use", {}).get("catalogs", {}) if isinstance(value, dict) else {}
    return isinstance(catalogs, dict) and any(
        isinstance(item, dict) and item.get("functions") for item in catalogs.values()
    )
