"""Reciprocal Rank Fusion.

RRF combines rankings from incomparable scoring spaces (BM25 raw scores
vs cosine similarity) using only ranks — no score calibration needed
(ADR-4): fused(d) = Σ_r weight_r / (k + rank_r(d)).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class FusedItem:
    id: str
    score: float
    # ranking name -> 1-based rank, for debuggability of every fused result
    ranks: dict[str, int] = field(default_factory=dict)


def reciprocal_rank_fusion(
    rankings: dict[str, list[str]],
    k: int = 60,
    weights: dict[str, float] | None = None,
) -> list[FusedItem]:
    """Fuse named *rankings* (ordered id lists) into one ranked list."""
    weights = weights or {}
    fused: dict[str, FusedItem] = {}
    for name, ids in rankings.items():
        weight = weights.get(name, 1.0)
        for rank, item_id in enumerate(ids, start=1):
            item = fused.setdefault(item_id, FusedItem(id=item_id, score=0.0))
            item.score += weight / (k + rank)
            item.ranks[name] = rank
    ordered = sorted(fused.values(), key=lambda i: i.score, reverse=True)
    return ordered
