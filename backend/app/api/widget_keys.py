"""Embed-widget key storage.

A widget key lets a site owner put EKIP's chat on their own website without
giving visitors a dashboard account. The signed JWT (see
core.security.create_widget_token) is the credential; this store only tracks
whether a given key id (``kid``) has been revoked — the secret itself is
never persisted, matching standard "shown once" API-key UX.
"""

from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class WidgetKey:
    kid: str
    user_id: int
    label: str
    created_at: str
    revoked: bool


class WidgetKeyStore:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS widget_keys ("
            " kid TEXT PRIMARY KEY,"
            " user_id INTEGER NOT NULL,"
            " label TEXT NOT NULL,"
            " created_at TEXT NOT NULL,"
            " revoked INTEGER NOT NULL DEFAULT 0)"
        )
        self._conn.commit()

    def create(self, user_id: int, label: str) -> WidgetKey:
        kid = uuid.uuid4().hex
        created_at = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            "INSERT INTO widget_keys (kid, user_id, label, created_at, revoked)"
            " VALUES (?, ?, ?, ?, 0)",
            (kid, user_id, label.strip() or "Website widget", created_at),
        )
        self._conn.commit()
        return WidgetKey(kid, user_id, label, created_at, False)

    def list(self, user_id: int) -> list[WidgetKey]:
        rows = self._conn.execute(
            "SELECT kid, user_id, label, created_at, revoked FROM widget_keys"
            " WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
        return [WidgetKey(kid, uid, label, created_at, bool(revoked))
                for kid, uid, label, created_at, revoked in rows]

    def is_active(self, kid: str) -> bool:
        row = self._conn.execute(
            "SELECT revoked FROM widget_keys WHERE kid = ?", (kid,)
        ).fetchone()
        return row is not None and row[0] == 0

    def revoke(self, kid: str, user_id: int) -> bool:
        cursor = self._conn.execute(
            "UPDATE widget_keys SET revoked = 1 WHERE kid = ? AND user_id = ?",
            (kid, user_id),
        )
        self._conn.commit()
        return cursor.rowcount > 0
