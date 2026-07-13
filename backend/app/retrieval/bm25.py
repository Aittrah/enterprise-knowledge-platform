"""In-process BM25 (Okapi) index.

Dense retrieval misses exactly what enterprises search for most — invoice
numbers, employee names, error codes, acronyms. BM25 nails those. This
index ingests the same ``VectorRecord``s as the vector store so the
indexer keeps both sides in sync.

In-memory by design for this milestone; it rebuilds from the store on
startup and can be swapped for PostgreSQL full-text search at scale.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from app.stores.base import Filters, VectorRecord
from app.stores.memory import matches

_TOKEN = re.compile(r"[a-z0-9][\w-]*")


def tokenize(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


@dataclass
class BM25Hit:
    id: str
    score: float
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


class BM25Index:
    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self._texts: dict[str, str] = {}
        self._metadata: dict[str, dict] = {}
        self._term_freqs: dict[str, Counter[str]] = {}
        self._doc_freq: Counter[str] = Counter()
        self._lengths: dict[str, int] = {}

    def __len__(self) -> int:
        return len(self._texts)

    def upsert(self, records: list[VectorRecord]) -> None:
        for record in records:
            if record.id in self._texts:
                self._remove(record.id)
            tokens = tokenize(record.text)
            self._texts[record.id] = record.text
            self._metadata[record.id] = record.metadata
            self._term_freqs[record.id] = Counter(tokens)
            self._lengths[record.id] = len(tokens)
            for term in set(tokens):
                self._doc_freq[term] += 1

    def delete_by_filter(self, filters: Filters) -> None:
        doomed = [
            doc_id
            for doc_id, meta in self._metadata.items()
            if matches(meta, filters)
        ]
        for doc_id in doomed:
            self._remove(doc_id)

    def _remove(self, doc_id: str) -> None:
        for term in set(self._term_freqs.pop(doc_id, ())):
            self._doc_freq[term] -= 1
            if self._doc_freq[term] <= 0:
                del self._doc_freq[term]
        self._texts.pop(doc_id, None)
        self._metadata.pop(doc_id, None)
        self._lengths.pop(doc_id, None)

    def search(
        self, query: str, top_k: int = 10, filters: Filters | None = None
    ) -> list[BM25Hit]:
        terms = tokenize(query)
        if not terms or not self._texts:
            return []
        total_docs = len(self._texts)
        avg_length = sum(self._lengths.values()) / total_docs

        hits: list[BM25Hit] = []
        for doc_id, freqs in self._term_freqs.items():
            if filters and not matches(self._metadata[doc_id], filters):
                continue
            score = 0.0
            length_norm = 1 - self.b + self.b * (self._lengths[doc_id] / avg_length)
            for term in terms:
                tf = freqs.get(term, 0)
                if tf == 0:
                    continue
                df = self._doc_freq[term]
                idf = math.log((total_docs - df + 0.5) / (df + 0.5) + 1)
                score += idf * (tf * (self.k1 + 1)) / (tf + self.k1 * length_norm)
            if score > 0:
                hits.append(
                    BM25Hit(doc_id, score, self._texts[doc_id], self._metadata[doc_id])
                )
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:top_k]
