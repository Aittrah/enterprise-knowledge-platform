"""PostgreSQL + pgvector store.

Secondary store per ADR-2: keeps chunks SQL-joinable for analytics and
serves as fallback when Qdrant is down. Uses psycopg3 (optional install);
metadata lives in JSONB, embeddings in a ``vector(dim)`` column with
cosine ops.
"""

from __future__ import annotations

import json
from typing import Any

from app.stores.base import Filters, SearchHit, StoreError, VectorRecord


def vector_literal(vector: list[float]) -> str:
    """pgvector input format: '[0.1,0.2,...]'."""
    return "[" + ",".join(repr(round(v, 8)) for v in vector) + "]"


def build_where(filters: Filters | None) -> tuple[str, list[Any]]:
    """Translate the common filter dict into a WHERE fragment + params."""
    if not filters:
        return "", []
    clauses, params = [], []
    for key, expected in filters.items():
        if isinstance(expected, (list, tuple, set)):
            clauses.append("metadata->>%s = ANY(%s)")
            params.extend([key, [str(v) for v in expected]])
        else:
            clauses.append("metadata->>%s = %s")
            params.extend([key, str(expected)])
    return " WHERE " + " AND ".join(clauses), params


class PgVectorStore:
    def __init__(self, dsn: str, table: str = "ekip_chunks") -> None:
        try:
            import psycopg
        except ImportError as exc:
            raise StoreError(
                "PgVectorStore needs `pip install psycopg[binary]`"
            ) from exc
        self._psycopg = psycopg
        self._dsn = dsn
        self._table = table
        self._dimension: int | None = None

    def _connect(self):
        try:
            return self._psycopg.connect(self._dsn)
        except Exception as exc:
            raise StoreError(f"PostgreSQL unreachable: {exc}") from exc

    def ensure_ready(self, dimension: int) -> None:
        self._dimension = dimension
        with self._connect() as conn:
            conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            conn.execute(
                f"CREATE TABLE IF NOT EXISTS {self._table} ("
                " id TEXT PRIMARY KEY,"
                " text TEXT NOT NULL,"
                " metadata JSONB NOT NULL DEFAULT '{}',"
                f" embedding vector({dimension}) NOT NULL)"
            )
            conn.commit()

    def upsert(self, records: list[VectorRecord]) -> None:
        if not records:
            return
        rows = [
            (r.id, r.text, json.dumps(r.metadata), vector_literal(r.vector))
            for r in records
        ]
        with self._connect() as conn:
            conn.cursor().executemany(
                f"INSERT INTO {self._table} (id, text, metadata, embedding)"
                " VALUES (%s, %s, %s, %s::vector)"
                " ON CONFLICT (id) DO UPDATE SET"
                " text = EXCLUDED.text, metadata = EXCLUDED.metadata,"
                " embedding = EXCLUDED.embedding",
                rows,
            )
            conn.commit()

    def search(
        self, vector: list[float], top_k: int = 10, filters: Filters | None = None
    ) -> list[SearchHit]:
        where, params = build_where(filters)
        literal = vector_literal(vector)
        query = (
            f"SELECT id, text, metadata, 1 - (embedding <=> %s::vector) AS score"
            f" FROM {self._table}{where} ORDER BY embedding <=> %s::vector LIMIT %s"
        )
        with self._connect() as conn:
            rows = conn.execute(query, [literal, *params, literal, top_k]).fetchall()
        return [
            SearchHit(rid, float(score), text, meta)
            for rid, text, meta, score in rows
        ]

    def delete_by_filter(self, filters: Filters) -> None:
        where, params = build_where(filters)
        if not where:
            return
        with self._connect() as conn:
            conn.execute(f"DELETE FROM {self._table}{where}", params)
            conn.commit()

    def count(self) -> int:
        with self._connect() as conn:
            return conn.execute(f"SELECT COUNT(*) FROM {self._table}").fetchone()[0]
