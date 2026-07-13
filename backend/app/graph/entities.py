"""Rule-based entity extraction.

Patterns + gazetteers keep this milestone dependency-free and fully
offline. Precision beats recall here: a noisy graph is worse than a sparse
one, so plain capitalized names require two capitalized words and pass a
stoplist. The LLM extractor (Phase 5) plugs in behind the same Entity
model to raise recall.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_TYPES = ("person", "organization", "department", "email", "money", "date")

_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b")
_MONEY = re.compile(
    r"(?:[$€£]\s?\d[\d,]*(?:\.\d{1,2})?)|(?:\b\d[\d,]*(?:\.\d{1,2})?\s?(?:USD|EUR|GBP|PKR)\b)"
)
_DATE = re.compile(
    r"\b\d{4}-\d{2}-\d{2}\b"
    r"|\b\d{1,2}[/.]\d{1,2}[/.]\d{2,4}\b"
    r"|\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\b"
    r"|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b",
    re.IGNORECASE,
)

_ORG_SUFFIX = (
    "Inc|Corp|Corporation|Ltd|LLC|GmbH|Company|Technologies|Solutions|Systems|"
    "Group|Holdings|Partners|Bank|University|Institute|Labs"
)
_ORG = re.compile(rf"\b(?:[A-Z][\w&.-]*\s)+(?:{_ORG_SUFFIX})\.?\b")

_HONORIFIC_PERSON = re.compile(
    r"\b(?:Mr|Ms|Mrs|Dr|Prof)\.?\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+){1,2})\b"
)
_PLAIN_PERSON = re.compile(r"\b([A-Z][a-z]{2,})\s([A-Z][a-z]{2,})\b")

_DEPARTMENTS = {
    "hr": "HR",
    "human resources": "Human Resources",
    "finance": "Finance",
    "legal": "Legal",
    "engineering": "Engineering",
    "operations": "Operations",
    "marketing": "Marketing",
    "sales": "Sales",
    "it": "IT",
    "research": "Research",
    "accounting": "Accounting",
}
_DEPARTMENT = re.compile(
    r"\b(" + "|".join(re.escape(d) for d in _DEPARTMENTS) + r")\b(?:\s+department)?",
    re.IGNORECASE,
)

# Capitalized words that are never part of a person's name.
_NAME_STOPLIST = frozenset(
    "January February March April May June July August September October November "
    "December Monday Tuesday Wednesday Thursday Friday Saturday Sunday The This "
    "New York Annual Leave Policy Employee Handbook Total Page Report Quarterly".split()
)


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().strip(".,;:")).lower()


@dataclass
class Entity:
    text: str
    type: str  # one of _TYPES
    source: str = ""  # document the entity was seen in
    mentions: int = 1
    extra: dict = field(default_factory=dict)

    @property
    def key(self) -> str:
        return f"{self.type}:{normalize(self.text)}"


class EntityExtractor:
    def extract(self, text: str, source: str = "") -> list[Entity]:
        found: dict[str, Entity] = {}
        taken_spans: list[tuple[int, int]] = []

        def add(raw: str, etype: str, span: tuple[int, int] | None = None) -> None:
            if span is not None:
                if any(s < span[1] and span[0] < e for s, e in taken_spans):
                    return  # overlaps a stronger match
                taken_spans.append(span)
            entity = Entity(text=raw.strip().rstrip("."), type=etype, source=source)
            existing = found.get(entity.key)
            if existing:
                existing.mentions += 1
            else:
                found[entity.key] = entity

        # Strong, unambiguous patterns claim their spans first.
        for match in _EMAIL.finditer(text):
            add(match.group(), "email", match.span())
        for match in _MONEY.finditer(text):
            add(match.group(), "money", match.span())
        for match in _DATE.finditer(text):
            add(match.group(), "date", match.span())
        for match in _ORG.finditer(text):
            add(match.group(), "organization", match.span())
        for match in _HONORIFIC_PERSON.finditer(text):
            add(match.group(1), "person", match.span())

        for match in _PLAIN_PERSON.finditer(text):
            first, last = match.group(1), match.group(2)
            if first in _NAME_STOPLIST or last in _NAME_STOPLIST:
                continue
            add(match.group(), "person", match.span())

        for match in _DEPARTMENT.finditer(text):
            span = match.span()
            if any(s < span[1] and span[0] < e for s, e in taken_spans):
                continue
            add(_DEPARTMENTS[match.group(1).lower()], "department")

        return list(found.values())
