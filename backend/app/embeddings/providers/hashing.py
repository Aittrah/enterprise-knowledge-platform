"""Deterministic feature-hashing embedder — the keyless fallback.

Hashes word unigrams and bigrams into a fixed-size signed vector and
L2-normalizes. No semantics, but lexically similar texts land close, which
is enough to develop and demo the whole retrieval stack (M9-M14) offline
with zero cost. Never ship it as the production embedder.
"""

from __future__ import annotations

import hashlib
import math
import re

from app.embeddings.base import InputType, Vector

_WORDS = re.compile(r"[a-z0-9]+")


class HashingProvider:
    name = "hashing"

    def __init__(self, dimension: int = 384) -> None:
        self.model = f"feature-hashing-{dimension}"
        self.dimension = dimension

    def embed(self, texts: list[str], input_type: InputType = "document") -> list[Vector]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> Vector:
        vector = [0.0] * self.dimension
        words = _WORDS.findall(text.lower())
        features = words + [f"{a}_{b}" for a, b in zip(words, words[1:])]
        for feature in features:
            digest = hashlib.blake2b(feature.encode(), digest_size=8).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            sign = 1.0 if digest[4] & 1 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(v * v for v in vector))
        if norm:
            vector = [v / norm for v in vector]
        return vector
