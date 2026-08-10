"""Durable workflow suspension signals."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class WorkflowSuspended(Exception):
    """Raised by a task that has persisted its continuation point elsewhere."""

    task: str
    resume_at: datetime
    reason: str = "timer"

    def __str__(self) -> str:
        return f"workflow suspended at {self.task!r} until {self.resume_at.isoformat()}"
