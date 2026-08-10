"""Loading and two-stage validation for OpenWorkflow documents."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from pydantic import ValidationError

from openworkflow_adk.models import AgentCharacteristics, OpenWorkflowDocument
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
        return {
            key: _strip_agent(item, key)
            for key, item in value.items()
            if key not in {"agent", "self_heal"}
            and not (parent == "use" and key in {"models", "providers", "memories"})
        }
    if isinstance(value, list):
        return [_strip_agent(item, parent) for item in value]
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
        agent = value.get("agent")
        if isinstance(agent, dict):
            for field, known, label in (
                ("memory", memories, "memory"),
                ("provider", providers, "provider"),
            ):
                reference = agent.get(field)
                if isinstance(reference, dict) and reference.get("use") not in known:
                    errors.append(
                        {
                            "path": f"{path}.agent.{field}.use",
                            "message": f"unknown {label} reference {reference.get('use')!r}",
                        }
                    )
            model = agent.get("model")
            if isinstance(model, dict):
                provider = model.get("provider")
                if isinstance(provider, dict) and provider.get("use") not in providers:
                    errors.append(
                        {
                            "path": f"{path}.agent.model.provider.use",
                            "message": f"unknown provider reference {provider.get('use')!r}",
                        }
                    )
        for key, item in value.items():
            errors.extend(_registry_reference_errors(item, providers, memories, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            errors.extend(_registry_reference_errors(item, providers, memories, f"{path}[{index}]"))
    return errors


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
        for key, item in value.items():
            errors.extend(_extension_errors(item, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            errors.extend(_extension_errors(item, f"{path}[{index}]"))
    return errors


def load(source: str | Path | dict[str, Any]) -> OpenWorkflowDocument:
    """Load YAML/JSON text, a file, or a mapping into a typed document."""
    raw = _parse_source(source)
    errors = _extension_errors(raw)
    model_registry = raw.get("use", {}).get("models", {})
    if isinstance(model_registry, dict):
        errors.extend(_model_reference_errors(raw, set(model_registry)))
    use = raw.get("use", {})
    if isinstance(use, dict):
        errors.extend(
            _registry_reference_errors(
                raw,
                set(use.get("providers", {})) if isinstance(use.get("providers"), dict) else set(),
                set(use.get("memories", {})) if isinstance(use.get("memories"), dict) else set(),
            )
        )
        model_defs = use.get("models", {})
        if isinstance(model_defs, dict):
            for model_name, model_def in model_defs.items():
                if not isinstance(model_def, dict):
                    continue
                provider = model_def.get("provider")
                if isinstance(provider, dict) and provider.get("use") not in set(
                    use.get("providers", {})
                ):
                    errors.append(
                        {
                            "path": f"$.use.models.{model_name}.provider.use",
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
