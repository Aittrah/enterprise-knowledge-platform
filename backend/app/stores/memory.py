"""Exact-search in-memory vector store.

Reference implementation of the ``VectorStore`` contract: unit tests run
against it, and paired with the ``hashing`` embedding provider it lets the
whole retrieval stack run with no services and no keys.
"""

from __future__ import annotations

import math

from app.stores.base import Filters, SearchHit, VectorRecord


def matches(metadata: dict, filters: Filters | None) -> bool:
    if not filters:
        return True
    for key, expected in filters.items():
        actual = metadata.get(key)
        if isinstance(expected, (list, tuple, set)):
            if actual not in expected:
                return False
        elif actual != expected:
            return False
    return True


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


class InMemoryVectorStore:
    def __init__(self) -> None:
        self._records: dict[str, VectorRecord] = {}
        self.dimension: int | None = None

    def ensure_ready(self, dimension: int) -> None:
        self.dimension = dimension

    def upsert(self, records: list[VectorRecord]) -> None:
        for record in records:
            self._records[record.id] = record

    def search(
        self, vector: list[float], top_k: int = 10, filters: Filters | None = None
    ) -> list[SearchHit]:
        candidates = (
            r for r in self._records.values() if matches(r.metadata, filters)
        )
        scored = [
            SearchHit(r.id, cosine(vector, r.vector), r.text, r.metadata)
            for r in candidates
        ]
        scored.sort(key=lambda hit: hit.score, reverse=True)
        return scored[:top_k]

    def delete_by_filter(self, filters: Filters) -> None:
        self._records = {
            rid: r for rid, r in self._records.items() if not matches(r.metadata, filters)
        }

    def count(self) -> int:
        return len(self._records)
