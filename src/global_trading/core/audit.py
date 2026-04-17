from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator


@dataclass
class AuditLog:
    """Append-only event log stored in SQLite."""

    db_path: str
    _uri: bool = False

    def __post_init__(self) -> None:
        if self.db_path == ":memory:":
            # Shared in-memory DB so each connection sees the same schema/data
            self.db_path = "file:mem_gtp_audit?mode=memory&cache=shared"
            self._uri = True

    def _connect(self) -> sqlite3.Connection:
        if self._uri:
            conn = sqlite3.connect(self.db_path, uri=True)
        else:
            path = Path(self.db_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(path)
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    def init(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload TEXT NOT NULL
                );
                """
            )
            conn.commit()

    def append(self, event_type: str, payload: dict[str, Any]) -> None:
        ts = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO audit_events (ts, event_type, payload) VALUES (?, ?, ?)",
                (ts, event_type, json.dumps(payload, default=str)),
            )
            conn.commit()

    def recent(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT ts, event_type, payload FROM audit_events ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        out: list[dict[str, Any]] = []
        for ts, event_type, payload in rows:
            out.append({"ts": ts, "event_type": event_type, "payload": json.loads(payload)})
        return out

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = self._connect()
        try:
            yield conn
        finally:
            conn.close()
