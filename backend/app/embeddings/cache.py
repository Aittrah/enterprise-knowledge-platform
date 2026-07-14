"""SQLite-backed embedding cache.

Embeddings are pure functions of (provider, model, input_type, text), so
caching is safe forever and saves real money: re-ingesting a 100-page
document with three edited paragraphs re-embeds three chunks, not all of
them. Vectors are stored as float32 blobs.
"""

from __future__ import annotations

import hashlib
import sqlite3
from array import array
from pathlib import Path

from app.embeddings.base import InputType, Vector


def cache_key(provider: str, model: str, input_type: InputType, text: str) -> str:
    payload = f"{provider}:{model}:{input_type}:{text}"
    return hashlib.blake2b(payload.encode(), digest_size=16).hexdigest()


class EmbeddingCache:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS embeddings ("
            " key TEXT PRIMARY KEY, dimension INTEGER NOT NULL, vector BLOB NOT NULL)"
        )
        self._conn.commit()

    def get_many(self, keys: list[str]) -> dict[str, Vector]:
        if not keys:
            return {}
        found: dict[str, Vector] = {}
        # SQLite caps bound parameters per statement; stay well under it.
        for start in range(0, len(keys), 500):
            batch = keys[start : start + 500]
            placeholders = ",".join("?" * len(batch))
            rows = self._conn.execute(
                f"SELECT key, vector FROM embeddings WHERE key IN ({placeholders})",
                batch,
            )
            for key, blob in rows:
                vec = array("f")
                vec.frombytes(blob)
                found[key] = vec.tolist()
        return found

    def set_many(self, items: dict[str, Vector]) -> None:
        if not items:
            return
        rows = [
            (key, len(vector), array("f", vector).tobytes())
            for key, vector in items.items()
        ]
        self._conn.executemany(
            "INSERT OR REPLACE INTO embeddings (key, dimension, vector) VALUES (?, ?, ?)",
            rows,
        )
        self._conn.commit()

    def __len__(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0]

    def close(self) -> None:
        self._conn.close()
