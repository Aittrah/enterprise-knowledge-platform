"""Dense semantic retrieval: embed the query, search the vector store.

The similarity threshold is the first groundedness control in the stack:
below it, a chunk is noise that would only pad the prompt and invite
hallucinated citations — better to return fewer, honest results.
"""

from __future__ import annotations

import time

from app.embeddings.service import EmbeddingService
from app.retrieval.base import RetrievalResult, RetrievedChunk
from app.stores.base import Filters, VectorStore


class DenseRetriever:
    name = "dense"

    def __init__(
        self,
        store: VectorStore,
        embeddings: EmbeddingService,
        min_score: float = 0.25,
    ) -> None:
        self._store = store
        self._embeddings = embeddings
        self.min_score = min_score

    def retrieve(
        self, query: str, top_k: int = 8, filters: Filters | None = None
    ) -> RetrievalResult:
        started = time.perf_counter()
        vector = self._embeddings.embed_query(query)
        hits = self._store.search(vector, top_k=top_k, filters=filters)
        kept = [h for h in hits if h.score >= self.min_score]
        return RetrievalResult(
            query=query,
            chunks=[RetrievedChunk(h.id, h.text, h.score, h.metadata) for h in kept],
            strategy=self.name,
            elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
            debug={
                "candidates": len(hits),
                "below_threshold": len(hits) - len(kept),
                "min_score": self.min_score,
            },
        )

    def similar(
        self, text: str, top_k: int = 5, exclude_id: str | None = None
    ) -> list[RetrievedChunk]:
        """Similarity search: chunks most like *text* (e.g. an existing
        chunk) — powers 'related passages' in the document preview."""
        vector = self._embeddings.embed_texts([text])[0]  # document-side embedding
        hits = self._store.search(vector, top_k=top_k + 1)
        chunks = [
            RetrievedChunk(h.id, h.text, h.score, h.metadata)
            for h in hits
            if h.id != exclude_id
        ]
        return chunks[:top_k]
