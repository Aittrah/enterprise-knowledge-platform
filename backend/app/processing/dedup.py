"""Duplicate detection: exact (content hash) and near-duplicate (MinHash

over word shingles). Near-duplicates are the common enterprise case — the
same policy paragraph pasted into ten documents with one word changed.

Candidate lookup is linear over stored signatures, which is fine for
per-document and small-corpus use; when the corpus outgrows it, the same
signatures drop into MinHash-LSH banding without changing callers.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from app.processing.normalize import normalize_text

_WORDS = re.compile(r"\w+")
_WS = re.compile(r"\s+")


def _fold(text: str) -> str:
    """Case/whitespace-insensitive comparison form. Digits are kept:
    'invoice 1' and 'invoice 2' are different content, not duplicates."""
    return _WS.sub(" ", normalize_text(text).lower()).strip()
_SHINGLE_SIZE = 5
_NUM_PERMUTATIONS = 32


def _shingles(text: str, k: int = _SHINGLE_SIZE) -> set[str]:
    words = _WORDS.findall(text.lower())
    if not words:
        return set()
    if len(words) <= k:
        return {" ".join(words)}
    return {" ".join(words[i : i + k]) for i in range(len(words) - k + 1)}


def _hash64(value: str, seed: int) -> int:
    digest = hashlib.blake2b(value.encode(), digest_size=8, salt=seed.to_bytes(2, "big"))
    return int.from_bytes(digest.digest(), "big")


def minhash_signature(text: str, num_perm: int = _NUM_PERMUTATIONS) -> tuple[int, ...]:
    shingles = _shingles(text)
    if not shingles:
        return ()
    return tuple(
        min(_hash64(shingle, seed) for shingle in shingles) for seed in range(num_perm)
    )


def estimate_similarity(a: tuple[int, ...], b: tuple[int, ...]) -> float:
    """Estimated Jaccard similarity of the underlying shingle sets."""
    if not a or not b or len(a) != len(b):
        return 0.0
    return sum(x == y for x, y in zip(a, b)) / len(a)


@dataclass
class DuplicateMatch:
    original_key: str
    kind: str  # "exact" | "near"
    similarity: float


class DeduplicationEngine:
    """Register texts under a key; each registration reports whether an
    already-registered text duplicates it."""

    def __init__(self, near_threshold: float = 0.9) -> None:
        self._near_threshold = near_threshold
        self._exact: dict[str, str] = {}  # content hash -> original key
        self._signatures: dict[str, tuple[int, ...]] = {}

    def check(self, text: str) -> DuplicateMatch | None:
        """Report a duplicate of *text* among registered texts, if any."""
        folded = _fold(text)
        content_hash = hashlib.sha256(folded.encode()).hexdigest()
        if content_hash in self._exact:
            return DuplicateMatch(self._exact[content_hash], "exact", 1.0)

        signature = minhash_signature(folded)
        best_key, best_score = None, 0.0
        for key, other in self._signatures.items():
            score = estimate_similarity(signature, other)
            if score > best_score:
                best_key, best_score = key, score
        if best_key is not None and best_score >= self._near_threshold:
            return DuplicateMatch(best_key, "near", round(best_score, 3))
        return None

    def add(self, key: str, text: str) -> None:
        folded = _fold(text)
        content_hash = hashlib.sha256(folded.encode()).hexdigest()
        self._exact.setdefault(content_hash, key)
        signature = minhash_signature(folded)
        if signature:
            self._signatures[key] = signature

    def check_and_add(self, key: str, text: str) -> DuplicateMatch | None:
        match = self.check(text)
        if match is None:
            self.add(key, text)
        return match
