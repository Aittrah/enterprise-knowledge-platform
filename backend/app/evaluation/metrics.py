"""Retrieval quality metrics. All operate on ranked source lists against a

set of relevant sources, so they work at chunk or document granularity.
"""

from __future__ import annotations


def precision_at_k(ranked: list[str], relevant: set[str], k: int) -> float:
    """Share of the top-k results that are relevant."""
    if k <= 0:
        return 0.0
    top = ranked[:k]
    if not top:
        return 0.0
    return sum(1 for item in top if item in relevant) / len(top)


def recall_at_k(ranked: list[str], relevant: set[str], k: int) -> float:
    """Share of the relevant items that appear in the top-k."""
    if not relevant:
        return 1.0
    return sum(1 for item in set(ranked[:k]) if item in relevant) / len(relevant)


def reciprocal_rank(ranked: list[str], relevant: set[str]) -> float:
    """1/rank of the first relevant result (0 when none appears)."""
    for index, item in enumerate(ranked, start=1):
        if item in relevant:
            return 1.0 / index
    return 0.0


def hit_rate(ranked: list[str], relevant: set[str], k: int) -> float:
    """1.0 when at least one relevant item is in the top-k."""
    return 1.0 if any(item in relevant for item in ranked[:k]) else 0.0


def percentile(values: list[float], pct: float) -> float:
    """Nearest-rank percentile (pct in 0..100)."""
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(1, round(pct / 100 * len(ordered)))
    return ordered[rank - 1]
