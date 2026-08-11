"""External function catalogs used by the spec-pure workflow flavor."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse
from urllib.request import url2pathname

import httpx
import yaml

from openworkflow_adk.errors import OpenWorkflowError
from openworkflow_adk.models import OpenWorkflowDocument, Task
from openworkflow_adk.security.security import validate_egress

__all__ = ["CatalogFunctionRegistry", "with_catalog_functions"]


class CatalogFunctionRegistry:
    """Load and cache named function sets shared by workflow runs."""

    def __init__(self) -> None:
        self._cache: dict[str, tuple[str, dict[str, dict[str, Any]]]] = {}

    def load(self, uri: str, *, base_dir: str | Path | None = None) -> dict[str, dict[str, Any]]:
        """Load a functions file from a local path, ``file://``, or HTTP(S) URI."""
        source = self._resolve_uri(uri, base_dir)
        if source.startswith(("http://", "https://")):
            validate_egress(source)
            # Do not follow redirects: every fetched URL must pass the egress
            # policy independently, otherwise a public URL can redirect to a
            # private address.
            response = httpx.get(source, timeout=30, follow_redirects=False)
            response.raise_for_status()
            text = response.text
            cache_key = source
        else:
            path = Path(source)
            text = path.read_text()
            cache_key = str(path.resolve())
        digest = hashlib.sha256(text.encode()).hexdigest()
        cached = self._cache.get(cache_key)
        if cached is not None and cached[0] == digest:
            return cached[1]
        try:
            raw = json.loads(text) if text.lstrip().startswith(("{", "[")) else yaml.safe_load(text)
        except (json.JSONDecodeError, yaml.YAMLError) as exc:
            raise ValueError(f"catalog functions file {uri!r} is not valid YAML/JSON") from exc
        if not isinstance(raw, dict) or not isinstance(raw.get("functions"), dict):
            raise ValueError("catalog functions file must contain a 'functions' object")
        functions: dict[str, dict[str, Any]] = {}
        for name, task in raw["functions"].items():
            if not isinstance(name, str) or not isinstance(task, dict):
                raise ValueError("catalog function names and tasks must be objects")
            try:
                functions[name] = Task.model_validate(task).model_dump(
                    by_alias=True, exclude_none=True
                )
            except Exception as exc:
                raise ValueError(f"invalid catalog function {name!r}: {exc}") from exc
        self._cache[cache_key] = (digest, functions)
        return functions

    @staticmethod
    def _resolve_uri(uri: str, base_dir: str | Path | None) -> str:
        parsed = urlparse(uri)
        if parsed.scheme in {"http", "https"}:
            return uri
        if parsed.scheme == "file":
            path = Path(url2pathname(unquote(parsed.path))).resolve()
            root = Path(base_dir or Path.cwd()).resolve()
            try:
                path.relative_to(root)
            except ValueError as exc:
                raise ValueError(f"catalog file {uri!r} escapes the catalog root") from exc
            return str(path)
        path = Path(uri)
        if not path.is_absolute() and base_dir is not None:
            path = Path(base_dir) / path
        path = path.resolve()
        if base_dir is not None:
            root = Path(base_dir).resolve()
            try:
                path.relative_to(root)
            except ValueError as exc:
                raise ValueError(f"catalog file {uri!r} escapes the catalog root") from exc
        return str(path)


def with_catalog_functions(
    document: OpenWorkflowDocument,
    registry: CatalogFunctionRegistry,
    *,
    base_dir: str | Path | None = None,
) -> OpenWorkflowDocument:
    """Return a document with catalog functions merged into ``use.functions``."""
    functions = dict(document.use.functions)
    owners: dict[str, str] = {name: "use.functions" for name in functions}
    for catalog_name in sorted(document.use.catalogs):
        catalog = document.use.catalogs[catalog_name]
        if not catalog.functions:
            continue
        for name, task in registry.load(catalog.functions, base_dir=base_dir).items():
            if name in functions:
                raise OpenWorkflowError(
                    title="ambiguous catalog function",
                    detail=f"function {name!r} is defined by {owners[name]} and {catalog_name!r}",
                )
            functions[name] = task
            owners[name] = catalog_name
    use = document.use.model_copy(update={"functions": functions})
    return document.model_copy(update={"use": use})
