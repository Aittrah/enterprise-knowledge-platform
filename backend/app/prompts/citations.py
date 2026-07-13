"""Citation rules and answer-side citation parsing."""

from __future__ import annotations

import re

CITATION_RULES = (
    "Cite every factual claim with the source number in square brackets, "
    "e.g. [1] or [2][3]. Only cite sources that actually support the claim. "
    "If the sources do not contain the answer, say so plainly instead of "
    "guessing — an honest \"the provided documents don't cover this\" is the "
    "correct answer. Never invent a citation number."
)

_CITATION = re.compile(r"\[(\d{1,3})\]")


def parse_citations(text: str) -> list[int]:
    """Unique citation numbers in order of first appearance."""
    seen: dict[int, None] = {}
    for match in _CITATION.finditer(text):
        seen.setdefault(int(match.group(1)))
    return list(seen)


def verify_citations(text: str, available: set[int]) -> list[int]:
    """Return citation numbers that do not resolve to a provided source —
    non-empty means the model invented a citation."""
    return [number for number in parse_citations(text) if number not in available]
