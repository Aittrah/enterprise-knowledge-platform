"""The Retriever API: the contract every retrieval strategy implements.

A ``RetrievedChunk`` is the unit the AI layer builds prompts and citations
from — id, text, score, and full provenance metadata travel together from
here to the final answer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from app.stores.base import Filters


@dataclass
class RetrievedChunk:
    id: str
    text: str
    score: float  # similarity in [0, 1]-ish space, higher is better
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def source(self) -> str:
        return str(self.metadata.get("source", ""))


@dataclass
class RetrievalResult:
    query: str
    chunks: list[RetrievedChunk] = field(default_factory=list)
    strategy: str = ""
    elapsed_ms: float = 0.0
    # Strategy-specific diagnostics (candidate counts, fusion details, ...).
    debug: dict[str, Any] = field(default_factory=dict)

    def __len__(self) -> int:
        return len(self.chunks)

    @property
    def sources(self) -> list[str]:
        seen: dict[str, None] = {}
        for chunk in self.chunks:
            seen.setdefault(chunk.source)
        return list(seen)


@runtime_checkable
class Retriever(Protocol):
    name: str

    def retrieve(
        self, query: str, top_k: int = 8, filters: Filters | None = None
    ) -> RetrievalResult: ...
