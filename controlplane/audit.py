import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from controlplane.redaction import redact_obj


class AuditLog:
    """Append-only record of every guard decision. Entries are never edited; PII is redacted
    before they are stored, in memory and on disk."""

    def __init__(self, path: Path | None = None):
        self.path = path
        self.events: list[dict[str, Any]] = []
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, **fields: Any) -> dict[str, Any]:
        event = redact_obj({"ts": datetime.now(UTC).isoformat(), **fields})
        self.events.append(event)
        if self.path is not None:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event, ensure_ascii=False) + "\n")
        return event
