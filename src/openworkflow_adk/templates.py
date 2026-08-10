"""Discoverable workflow template catalog helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_template_catalog(root: str | Path) -> list[dict[str, Any]]:
    """Load and validate an examples catalog rooted at ``root``."""
    directory = Path(root)
    catalog = json.loads((directory / "catalog.json").read_text())
    if not isinstance(catalog, list):
        raise ValueError("template catalog must be an array")
    for item in catalog:
        if not isinstance(item, dict) or not isinstance(item.get("file"), str):
            raise ValueError("template entries require a file")
        if not (directory / item["file"]).is_file():
            raise FileNotFoundError(directory / item["file"])
    return catalog
