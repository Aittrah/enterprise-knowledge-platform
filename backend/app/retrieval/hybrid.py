"""Hybrid retrieval engine: dense vectors + BM25 + metadata filters,

fused with RRF. Scores are normalized so the top hit is 1.0 — downstream
consumers (confidence UI, reranker) get a stable scale regardless of how
many rankings contributed.
"""

from __future__ import annotations

import time

from app.embeddings.service import EmbeddingService
from app.retrieval.base import RetrievalResult, RetrievedChunk
from app.retrieval.bm25 import BM25Index
from app.retrieval.fusion import reciprocal_rank_fusion
from app.stores.base import Filters, VectorStore


class HybridRetriever:
    name = "hybrid"

    def __init__(
        self,
        store: VectorStore,
        embeddings: EmbeddingService,
        bm25: BM25Index,
        candidates: int = 50,
        rrf_k: int = 60,
        dense_weight: float = 1.0,
        bm25_weight: float = 1.0,
    ) -> None:
        self._store = store
        self._embeddings = embeddings
        self._bm25 = bm25
        self._candidates = candidates
        self._rrf_k = rrf_k
        self._weights = {"dense": dense_weight, "bm25": bm25_weight}

    def retrieve(
        self, query: str, top_k: int = 8, filters: Filters | None = None
    ) -> RetrievalResult:
        started = time.perf_counter()

        vector = self._embeddings.embed_query(query)
        dense_hits = self._store.search(vector, top_k=self._candidates, filters=filters)
        bm25_hits = self._bm25.search(query, top_k=self._candidates, filters=filters)

        payloads = {h.id: (h.text, h.metadata) for h in dense_hits}
        payloads.update({h.id: (h.text, h.metadata) for h in bm25_hits})

        fused = reciprocal_rank_fusion(
            {
                "dense": [h.id for h in dense_hits],
                "bm25": [h.id for h in bm25_hits],
            },
            k=self._rrf_k,
            weights=self._weights,
        )[:top_k]

        top_score = fused[0].score if fused else 1.0
        chunks = []
        for item in fused:
            text, metadata = payloads[item.id]
            chunks.append(
                RetrievedChunk(
                    id=item.id,
                    text=text,
                    score=round(item.score / top_score, 4),
                    metadata={**metadata, "fusion_ranks": item.ranks},
                )
            )

        overlap = {h.id for h in dense_hits} & {h.id for h in bm25_hits}
        return RetrievalResult(
            query=query,
            chunks=chunks,
            strategy=self.name,
            elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
            debug={
                "dense_candidates": len(dense_hits),
                "bm25_candidates": len(bm25_hits),
                "overlap": len(overlap),
                "rrf_k": self._rrf_k,
                "weights": self._weights,
            },
        )
