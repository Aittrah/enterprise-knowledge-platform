"""Vector store contract.

Filters are plain dicts: ``{"source": "policy.pdf"}`` matches equality,
``{"file_type": ["pdf", "docx"]}`` matches membership. Each backend
translates that to its native filter syntax, so retrieval code (M11-M14)
never knows which store it is talking to.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

Filters = dict[str, Any]


class StoreError(Exception):
    """A storage backend failed or is misconfigured."""


@dataclass
class VectorRecord:
    """One stored chunk: id + embedding + text + provenance payload."""

    id: str
    vector: list[float]
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchHit:
    id: str
    score: float  # cosine similarity, higher is better
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class VectorStore(Protocol):
    def ensure_ready(self, dimension: int) -> None:
        """Create the collection/schema for vectors of *dimension* if needed."""
        ...

    def upsert(self, records: list[VectorRecord]) -> None: ...

    def search(
        self, vector: list[float], top_k: int = 10, filters: Filters | None = None
    ) -> list[SearchHit]: ...

    def delete_by_filter(self, filters: Filters) -> None: ...

    def count(self) -> int: ...
