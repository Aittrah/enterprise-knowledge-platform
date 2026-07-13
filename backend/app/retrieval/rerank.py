"""Reranking module.

First-stage retrieval (dense/hybrid) optimizes recall over millions of
chunks; a reranker reads the query against each surviving candidate and
re-scores with far more precision. Backends:

    CohereReranker        — Cohere Rerank v2 REST API
    CrossEncoderReranker  — local sentence-transformers cross-encoder
    LexicalReranker       — keyless offline fallback (term overlap)

``RerankedRetriever`` composes any ``Retriever`` with any ``Reranker``
while preserving the Retriever contract, so the AI layer doesn't know
whether reranking is on.
"""

from __future__ import annotations

import re
import time
from typing import Protocol, runtime_checkable

import httpx

from app.embeddings.base import ProviderConfigurationError
from app.embeddings.providers.http import post_json, require_api_key
from app.retrieval.base import RetrievalResult, RetrievedChunk, Retriever
from app.stores.base import Filters


@runtime_checkable
class Reranker(Protocol):
    name: str

    def rerank(
        self, query: str, chunks: list[RetrievedChunk], top_k: int
    ) -> list[RetrievedChunk]:
        """Return the *top_k* chunks re-scored and re-ordered by relevance
        to *query*. Chunk scores are replaced; retrieval scores should be
        preserved by the caller if needed."""
        ...


class CohereReranker:
    name = "cohere-rerank"

    def __init__(
        self,
        model: str = "rerank-english-v3.0",
        api_key: str | None = None,
        base_url: str = "https://api.cohere.com/v2",
        client: httpx.Client | None = None,
    ) -> None:
        self.model = model
        self._api_key = require_api_key("COHERE_API_KEY", api_key)
        self._url = f"{base_url}/rerank"
        self._client = client or httpx.Client()

    def rerank(
        self, query: str, chunks: list[RetrievedChunk], top_k: int
    ) -> list[RetrievedChunk]:
        if not chunks:
            return []
        data = post_json(
            self._client,
            self._url,
            headers={"Authorization": f"Bearer {self._api_key}"},
            payload={
                "model": self.model,
                "query": query,
                "documents": [c.text for c in chunks],
                "top_n": top_k,
            },
        )
        reranked = []
        for row in data["results"]:
            chunk = chunks[row["index"]]
            chunk.score = round(float(row["relevance_score"]), 4)
            reranked.append(chunk)
        return reranked


class CrossEncoderReranker:
    """Local cross-encoder (optional: `pip install sentence-transformers`)."""

    name = "cross-encoder"

    def __init__(self, model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2") -> None:
        self.model = model
        try:
            from sentence_transformers import CrossEncoder
        except ImportError as exc:
            raise ProviderConfigurationError(
                "CrossEncoderReranker needs `pip install sentence-transformers` "
                "(pulls in torch). Use CohereReranker or LexicalReranker instead."
            ) from exc
        self._encoder = CrossEncoder(model)

    def rerank(
        self, query: str, chunks: list[RetrievedChunk], top_k: int
    ) -> list[RetrievedChunk]:
        if not chunks:
            return []
        scores = self._encoder.predict([(query, c.text) for c in chunks])
        for chunk, score in zip(chunks, scores):
            chunk.score = round(float(score), 4)
        return sorted(chunks, key=lambda c: c.score, reverse=True)[:top_k]


_WORDS = re.compile(r"[a-z0-9][\w-]*")
_STOP = frozenset(
    "the a an and or of to in for on at by is are was were be do does how what "
    "when where why who which with from that this these those i you we they it".split()
)


class LexicalReranker:
    """Keyless fallback: content-word overlap with an adjacency bonus.

    Far weaker than a cross-encoder, but deterministic and free — it keeps
    the full retrieval pipeline exercisable offline, and its interface is
    identical to the paid backends."""

    name = "lexical"

    def rerank(
        self, query: str, chunks: list[RetrievedChunk], top_k: int
    ) -> list[RetrievedChunk]:
        query_words = [w for w in _WORDS.findall(query.lower()) if w not in _STOP]
        if not query_words:
            return chunks[:top_k]
        query_bigrams = set(zip(query_words, query_words[1:]))

        for chunk in chunks:
            text_words = [w for w in _WORDS.findall(chunk.text.lower()) if w not in _STOP]
            text_set = set(text_words)
            overlap = sum(1 for w in query_words if w in text_set) / len(query_words)
            bigram_bonus = 0.0
            if query_bigrams:
                text_bigrams = set(zip(text_words, text_words[1:]))
                bigram_bonus = 0.5 * len(query_bigrams & text_bigrams) / len(query_bigrams)
            # Normalize (max overlap 1.0 + max bonus 0.5) into [0, 1] —
            # clamping instead would erase the phrase bonus at full overlap.
            chunk.score = round((overlap + bigram_bonus) / 1.5, 4)

        return sorted(chunks, key=lambda c: c.score, reverse=True)[:top_k]


class RerankedRetriever:
    """Retrieve wide (candidate_k), rerank narrow (top_k)."""

    def __init__(
        self, retriever: Retriever, reranker: Reranker, candidate_k: int = 30
    ) -> None:
        self._retriever = retriever
        self._reranker = reranker
        self._candidate_k = candidate_k
        self.name = f"{retriever.name}+{reranker.name}"

    def retrieve(
        self, query: str, top_k: int = 8, filters: Filters | None = None
    ) -> RetrievalResult:
        started = time.perf_counter()
        first_stage = self._retriever.retrieve(
            query, top_k=self._candidate_k, filters=filters
        )
        for chunk in first_stage.chunks:
            chunk.metadata["retrieval_score"] = chunk.score

        reranked = self._reranker.rerank(query, first_stage.chunks, top_k)
        return RetrievalResult(
            query=query,
            chunks=reranked,
            strategy=self.name,
            elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
            debug={
                **first_stage.debug,
                "first_stage": self._retriever.name,
                "first_stage_ms": first_stage.elapsed_ms,
                "reranker": self._reranker.name,
                "candidates_reranked": len(first_stage.chunks),
            },
        )
