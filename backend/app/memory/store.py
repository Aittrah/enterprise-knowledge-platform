"""SQLite persistence for messages and facts.

One file, two tables. Messages are the raw conversation record; facts are
distilled knowledge scoped to a user, a project, or a conversation summary.
Postgres replaces this behind the same interface at M18.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

SCOPES = ("user", "project", "conversation")


@dataclass
class StoredMessage:
    id: int
    conversation_id: str
    role: str
    content: str
    created_at: str


@dataclass
class StoredFact:
    id: int
    scope: str
    scope_id: str
    kind: str  # "fact" | "summary"
    content: str
    created_at: str


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MemoryStore:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path))
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_messages_conversation
                ON messages(conversation_id, id);
            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scope TEXT NOT NULL,
                scope_id TEXT NOT NULL,
                kind TEXT NOT NULL DEFAULT 'fact',
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_facts_scope ON facts(scope, scope_id);
            """
        )
        self._conn.commit()

    # -- messages ---------------------------------------------------------------

    def add_message(self, conversation_id: str, role: str, content: str) -> int:
        cursor = self._conn.execute(
            "INSERT INTO messages (conversation_id, role, content, created_at)"
            " VALUES (?, ?, ?, ?)",
            (conversation_id, role, content, _now()),
        )
        self._conn.commit()
        return int(cursor.lastrowid)

    def messages(self, conversation_id: str) -> list[StoredMessage]:
        rows = self._conn.execute(
            "SELECT id, conversation_id, role, content, created_at FROM messages"
            " WHERE conversation_id = ? ORDER BY id",
            (conversation_id,),
        ).fetchall()
        return [StoredMessage(*row) for row in rows]

    def conversations(self) -> list[str]:
        rows = self._conn.execute(
            "SELECT conversation_id, MAX(id) AS last FROM messages"
            " GROUP BY conversation_id ORDER BY last DESC"
        ).fetchall()
        return [row[0] for row in rows]

    # -- facts --------------------------------------------------------------------

    def add_fact(self, scope: str, scope_id: str, content: str, kind: str = "fact") -> int:
        if scope not in SCOPES:
            raise ValueError(f"scope must be one of {SCOPES}, got '{scope}'")
        cursor = self._conn.execute(
            "INSERT INTO facts (scope, scope_id, kind, content, created_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (scope, scope_id, kind, content, _now()),
        )
        self._conn.commit()
        return int(cursor.lastrowid)

    def facts(self, scope: str, scope_id: str) -> list[StoredFact]:
        rows = self._conn.execute(
            "SELECT id, scope, scope_id, kind, content, created_at FROM facts"
            " WHERE scope = ? AND scope_id = ? ORDER BY id",
            (scope, scope_id),
        ).fetchall()
        return [StoredFact(*row) for row in rows]

    def delete_fact(self, fact_id: int) -> bool:
        cursor = self._conn.execute("DELETE FROM facts WHERE id = ?", (fact_id,))
        self._conn.commit()
        return cursor.rowcount > 0

    def close(self) -> None:
        self._conn.close()
