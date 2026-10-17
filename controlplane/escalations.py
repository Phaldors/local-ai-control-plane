"""Persistent queue of actions held for a human, with an append-only decision log.

The guard (or the MCP host) *creates* an escalation; only a human channel *decides* it. The model
has no way to reach `decide`: it is not an MCP tool and the MCP server never imports the console.
Rules the store enforces itself, so a buggy or hostile caller cannot bend them:

- a decision is allowed only from `pending`, atomically (a double click or a race cannot decide
  twice);
- the event log is append-only (SQLite triggers reject UPDATE and DELETE on it);
- everything stored is PII-redacted.
"""

import json
import sqlite3
import threading
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from controlplane.redaction import redact_obj

Status = Literal["pending", "approved", "rejected"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS escalations (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    tool TEXT NOT NULL,
    arguments TEXT NOT NULL,
    rule TEXT NOT NULL,
    reason TEXT NOT NULL,
    source TEXT NOT NULL,
    user_request TEXT,
    case_id TEXT,
    status TEXT NOT NULL DEFAULT 'pending'
);
CREATE TABLE IF NOT EXISTS events (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    escalation_id TEXT NOT NULL,
    ts TEXT NOT NULL,
    type TEXT NOT NULL,
    actor TEXT NOT NULL,
    note TEXT,
    details TEXT
);
CREATE TRIGGER IF NOT EXISTS events_no_update BEFORE UPDATE ON events
BEGIN SELECT RAISE(ABORT, 'events are append-only'); END;
CREATE TRIGGER IF NOT EXISTS events_no_delete BEFORE DELETE ON events
BEGIN SELECT RAISE(ABORT, 'events are append-only'); END;
"""


class AlreadyDecided(Exception):
    """The escalation is no longer pending."""


class NotFound(Exception):
    pass


@dataclass(frozen=True)
class Escalation:
    id: str
    created_at: str
    tool: str
    arguments: dict[str, Any]
    rule: str
    reason: str
    source: str  # "server" (guard behind the tools) or "host" (provenance in the MCP host)
    user_request: str | None
    case_id: str | None
    status: Status

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _now() -> str:
    return datetime.now(UTC).isoformat()


class EscalationStore:
    def __init__(self, path: str | Path = ":memory:"):
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock, self._conn:
            self._conn.executescript(SCHEMA)

    # --- producers (guard, host) ---
    def create(
        self,
        tool: str,
        arguments: dict[str, Any],
        rule: str,
        reason: str,
        source: str,
        user_request: str | None = None,
        case_id: str | None = None,
    ) -> Escalation:
        safe = redact_obj({"arguments": arguments, "user_request": user_request, "reason": reason})
        with self._lock, self._conn:
            count = self._conn.execute("SELECT COUNT(*) FROM escalations").fetchone()[0]
            esc_id = f"ESC-{count + 1:04d}"
            self._conn.execute(
                "INSERT INTO escalations (id, created_at, tool, arguments, rule, reason, source,"
                " user_request, case_id) VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    esc_id,
                    _now(),
                    tool,
                    json.dumps(safe["arguments"], ensure_ascii=False),
                    rule,
                    safe["reason"],
                    source,
                    safe["user_request"],
                    case_id,
                ),
            )
            self._event(esc_id, "created", source, None, {"rule": rule})
        return self.get(esc_id)

    # --- the human channel ---
    def decide(
        self, esc_id: str, decision: Literal["approved", "rejected"], actor: str, note: str | None
    ) -> Escalation:
        safe_note = redact_obj(note)
        with self._lock, self._conn:
            cursor = self._conn.execute(
                "UPDATE escalations SET status=? WHERE id=? AND status='pending'",
                (decision, esc_id),
            )
            if cursor.rowcount == 0:
                exists = self._conn.execute("SELECT 1 FROM escalations WHERE id=?", (esc_id,))
                if exists.fetchone() is None:
                    raise NotFound(esc_id)
                raise AlreadyDecided(esc_id)
            self._event(esc_id, decision, actor, safe_note, None)
        return self.get(esc_id)

    def record(
        self, esc_id: str, type_: str, actor: str, note: str | None, details: Any = None
    ) -> None:
        """Append a non-deciding event (e.g. execution result, refused approval)."""
        with self._lock, self._conn:
            self._event(esc_id, type_, actor, redact_obj(note), details)

    # --- reads ---
    def get(self, esc_id: str) -> Escalation:
        with self._lock:
            row = self._conn.execute("SELECT * FROM escalations WHERE id=?", (esc_id,)).fetchone()
        if row is None:
            raise NotFound(esc_id)
        return self._row(row)

    def list_escalations(self, status: Status | None = None) -> list[Escalation]:
        query, params = "SELECT * FROM escalations", ()
        if status:
            query, params = query + " WHERE status=?", (status,)
        with self._lock:
            rows = self._conn.execute(query + " ORDER BY created_at, id", params).fetchall()
        return [self._row(r) for r in rows]

    def events(self, esc_id: str | None = None) -> list[dict[str, Any]]:
        query, params = "SELECT * FROM events", ()
        if esc_id:
            query, params = query + " WHERE escalation_id=?", (esc_id,)
        with self._lock:
            rows = self._conn.execute(query + " ORDER BY seq", params).fetchall()
        return [
            {
                "seq": r["seq"],
                "escalation_id": r["escalation_id"],
                "ts": r["ts"],
                "type": r["type"],
                "actor": r["actor"],
                "note": r["note"],
                "details": json.loads(r["details"]) if r["details"] else None,
            }
            for r in rows
        ]

    # --- internals ---
    def _event(self, esc_id: str, type_: str, actor: str, note: str | None, details: Any) -> None:
        self._conn.execute(
            "INSERT INTO events (escalation_id, ts, type, actor, note, details)"
            " VALUES (?,?,?,?,?,?)",
            (
                esc_id,
                _now(),
                type_,
                actor,
                note,
                json.dumps(redact_obj(details), ensure_ascii=False)
                if details is not None
                else None,
            ),
        )

    @staticmethod
    def _row(row: sqlite3.Row) -> Escalation:
        return Escalation(
            id=row["id"],
            created_at=row["created_at"],
            tool=row["tool"],
            arguments=json.loads(row["arguments"]),
            rule=row["rule"],
            reason=row["reason"],
            source=row["source"],
            user_request=row["user_request"],
            case_id=row["case_id"],
            status=row["status"],
        )
