"""Prompt-injection and jailbreak detection.

Pattern-scored screening runs on every user input before it reaches the
LLM. Heuristics catch the well-known attack families cheaply and offline;
a classifier model can replace the scorer behind the same verdict shape.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# (pattern, weight, category). Weights accumulate; >= threshold blocks.
_SIGNALS: list[tuple[re.Pattern[str], float, str]] = [
    # -- instruction override (injection) --
    (re.compile(r"\bignore\s+(all\s+|any\s+)?(previous|prior|above|earlier)\s+(instructions?|prompts?|rules?)", re.I), 1.0, "injection"),
    (re.compile(r"\bdisregard\s+(the\s+)?(above|previous|system)", re.I), 1.0, "injection"),
    (re.compile(r"\b(reveal|show|print|repeat|output)\b.{0,40}\b(system\s+prompt|hidden\s+instructions?|initial\s+prompt)", re.I), 1.0, "injection"),
    (re.compile(r"\bnew\s+instructions?\s*:", re.I), 0.8, "injection"),
    (re.compile(r"\byou\s+are\s+now\s+(?!able)", re.I), 0.6, "injection"),
    (re.compile(r"<\s*/?\s*system\s*>", re.I), 0.9, "injection"),
    # -- persona / jailbreak --
    (re.compile(r"\b(DAN|do\s+anything\s+now)\b", re.I), 0.9, "jailbreak"),
    (re.compile(r"\b(developer|god|sudo|unrestricted|jailbreak(ed)?)\s+mode\b", re.I), 0.9, "jailbreak"),
    (re.compile(r"\bpretend\s+(you|to)\b.{0,50}\b(no\s+(rules|restrictions|guidelines)|anything)", re.I), 0.8, "jailbreak"),
    (re.compile(r"\bwithout\s+(any\s+)?(restrictions?|filters?|limitations?|censorship)", re.I), 0.7, "jailbreak"),
    (re.compile(r"\bhypothetically\b.{0,60}\b(bypass|evade|circumvent)", re.I), 0.7, "jailbreak"),
    # -- smuggling --
    (re.compile(r"\b(base64|rot13)\s*(decode|encoded?)\b", re.I), 0.5, "smuggling"),
    (re.compile(r"[A-Za-z0-9+/]{80,}={0,2}"), 0.5, "smuggling"),
]

_BLOCK_THRESHOLD = 1.0


@dataclass
class InputVerdict:
    allowed: bool
    score: float
    categories: list[str] = field(default_factory=list)
    matched: list[str] = field(default_factory=list)  # matched snippets, for audit


class InjectionDetector:
    def __init__(self, threshold: float = _BLOCK_THRESHOLD) -> None:
        self._threshold = threshold

    def screen(self, text: str) -> InputVerdict:
        score = 0.0
        categories: dict[str, None] = {}
        matched: list[str] = []
        for pattern, weight, category in _SIGNALS:
            found = pattern.search(text)
            if found:
                score += weight
                categories.setdefault(category)
                matched.append(found.group()[:60])
        return InputVerdict(
            allowed=score < self._threshold,
            score=round(score, 2),
            categories=list(categories),
            matched=matched,
        )
