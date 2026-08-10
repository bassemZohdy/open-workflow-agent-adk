"""Tamper-evident audit records for workflow management actions."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class AuditEntry:
    timestamp: str
    subject: str
    action: str
    resource: str
    details: dict[str, Any]
    previous_hash: str
    digest: str


@dataclass
class AuditLog:
    entries: list[AuditEntry] = field(default_factory=list)

    def append(
        self, subject: str, action: str, resource: str, details: dict[str, Any] | None = None
    ) -> AuditEntry:
        timestamp = datetime.now(timezone.utc).isoformat()
        previous_hash = self.entries[-1].digest if self.entries else ""
        payload = {
            "timestamp": timestamp,
            "subject": subject,
            "action": action,
            "resource": resource,
            "details": details or {},
            "previous_hash": previous_hash,
        }
        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        entry = AuditEntry(**payload, digest=digest)
        self.entries.append(entry)
        return entry

    def verify(self) -> bool:
        previous_hash = ""
        for entry in self.entries:
            payload = {
                "timestamp": entry.timestamp,
                "subject": entry.subject,
                "action": entry.action,
                "resource": entry.resource,
                "details": entry.details,
                "previous_hash": previous_hash,
            }
            expected = hashlib.sha256(
                json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            if entry.digest != expected or entry.previous_hash != previous_hash:
                return False
            previous_hash = entry.digest
        return True
