"""Token cost estimation (USD per 1M tokens; update alongside provider

pricing pages). Unknown models estimate at the default rate and are marked.
"""

from __future__ import annotations

# (input per 1M, output per 1M)
_PRICES: dict[str, tuple[float, float]] = {
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    "text-embedding-3-small": (0.02, 0.0),
    "text-embedding-3-large": (0.13, 0.0),
    "embed-english-v3.0": (0.10, 0.0),
    "voyage-3": (0.06, 0.0),
    "rerank-english-v3.0": (2.00, 0.0),  # per 1M rank units, approximate
    "extractive": (0.0, 0.0),
    "feature-hashing-384": (0.0, 0.0),
}
_DEFAULT = (1.00, 3.00)


def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int = 0) -> dict:
    known = model in _PRICES
    input_rate, output_rate = _PRICES.get(model, _DEFAULT)
    cost = (prompt_tokens * input_rate + completion_tokens * output_rate) / 1_000_000
    return {"model": model, "usd": round(cost, 6), "estimated": not known}
