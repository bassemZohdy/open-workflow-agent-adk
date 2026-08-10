"""Structured run logging hooks."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from typing import Any, TextIO


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


class JsonRunLogger:
    """Emit one JSON object per run/task lifecycle event."""

    def __init__(self, stream: TextIO = sys.stderr) -> None:
        self.stream = stream

    def __call__(self, record: dict[str, Any]) -> None:
        self.stream.write(json.dumps({"timestamp": _timestamp(), **record}, default=str) + "\n")
        self.stream.flush()
