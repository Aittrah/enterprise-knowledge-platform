"""EmbeddingService: cache-first, deduplicated, batched, retrying.

The only path through which the rest of the platform embeds anything —
so cost controls (cache, dedupe, batch) apply everywhere by construction.
"""

from __future__ import annotations

import time
from pathlib import Path

from app.embeddings.base import (
    EmbeddingProvider,
    InputType,
    ProviderRequestError,
    Vector,
)
from app.embeddings.cache import EmbeddingCache, cache_key


class EmbeddingService:
    def __init__(
        self,
        provider: EmbeddingProvider,
        cache_path: Path | None = None,
        cache: EmbeddingCache | None = None,
        batch_size: int = 64,
        max_retries: int = 3,
        backoff_seconds: float = 1.0,
    ) -> None:
        self.provider = provider
        self._cache = cache or (EmbeddingCache(cache_path) if cache_path else None)
        self._batch_size = batch_size
        self._max_retries = max_retries
        self._backoff = backoff_seconds
        self.stats = {"cache_hits": 0, "cache_misses": 0, "provider_batches": 0}

    def embed_texts(
        self, texts: list[str], input_type: InputType = "document"
    ) -> list[Vector]:
        if not texts:
            return []

        unique = list(dict.fromkeys(texts))
        keys = {
            text: cache_key(self.provider.name, self.provider.model, input_type, text)
            for text in unique
        }
        cached = (
            self._cache.get_many(list(keys.values())) if self._cache is not None else {}
        )
        vectors: dict[str, Vector] = {
            text: cached[key] for text, key in keys.items() if key in cached
        }
        misses = [text for text in unique if text not in vectors]
        self.stats["cache_hits"] += len(unique) - len(misses)
        self.stats["cache_misses"] += len(misses)

        for start in range(0, len(misses), self._batch_size):
            batch = misses[start : start + self._batch_size]
            embedded = self._embed_with_retry(batch, input_type)
            if len(embedded) != len(batch):
                raise ProviderRequestError(
                    f"{self.provider.name} returned {len(embedded)} vectors "
                    f"for {len(batch)} inputs"
                )
            vectors.update(zip(batch, embedded))
            if self._cache is not None:
                self._cache.set_many({keys[t]: v for t, v in zip(batch, embedded)})

        return [vectors[text] for text in texts]

    def embed_query(self, text: str) -> Vector:
        return self.embed_texts([text], input_type="query")[0]

    def _embed_with_retry(self, batch: list[str], input_type: InputType) -> list[Vector]:
        last_error: Exception | None = None
        for attempt in range(self._max_retries):
            try:
                self.stats["provider_batches"] += 1
                return self.provider.embed(batch, input_type=input_type)
            except ProviderRequestError as exc:
                last_error = exc
                if attempt < self._max_retries - 1:
                    time.sleep(self._backoff * (2**attempt))
        raise last_error  # type: ignore[misc]
