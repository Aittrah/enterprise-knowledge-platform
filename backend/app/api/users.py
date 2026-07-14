"""User storage (SQLite) with role-based access.

The first registered account becomes the admin — standard bootstrap for
self-hosted deployments.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.core.security import hash_password, verify_password


@dataclass
class User:
    id: int
    email: str
    name: str
    role: str  # "admin" | "user"
    created_at: str


class UserExistsError(Exception):
    pass


class UserStore:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS users ("
            " id INTEGER PRIMARY KEY AUTOINCREMENT,"
            " email TEXT UNIQUE NOT NULL,"
            " name TEXT NOT NULL,"
            " password_hash TEXT NOT NULL,"
            " role TEXT NOT NULL,"
            " created_at TEXT NOT NULL)"
        )
        self._conn.commit()

    def create(self, email: str, password: str, name: str) -> User:
        email = email.strip().lower()
        role = "admin" if self.count() == 0 else "user"
        try:
            cursor = self._conn.execute(
                "INSERT INTO users (email, name, password_hash, role, created_at)"
                " VALUES (?, ?, ?, ?, ?)",
                (
                    email,
                    name.strip(),
                    hash_password(password),
                    role,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            self._conn.commit()
        except sqlite3.IntegrityError:
            raise UserExistsError(f"account already exists for {email}") from None
        return self.get(int(cursor.lastrowid))

    def authenticate(self, email: str, password: str) -> User | None:
        row = self._conn.execute(
            "SELECT id, password_hash FROM users WHERE email = ?",
            (email.strip().lower(),),
        ).fetchone()
        if row and verify_password(password, row[1]):
            return self.get(row[0])
        return None

    def get(self, user_id: int) -> User:
        row = self._conn.execute(
            "SELECT id, email, name, role, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"no user {user_id}")
        return User(*row)

    def list(self) -> list[User]:
        rows = self._conn.execute(
            "SELECT id, email, name, role, created_at FROM users ORDER BY id"
        ).fetchall()
        return [User(*row) for row in rows]

    def count(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
