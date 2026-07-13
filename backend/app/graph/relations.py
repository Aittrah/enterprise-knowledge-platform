"""Relation detection between entities that share a sentence.

Verb-cue patterns give typed edges; anything else that co-occurs gets a
weak generic edge. Every relation keeps its evidence sentence so the UI
(and the compliance officer) can always answer "why is this edge here?".
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.graph.entities import Entity

_SENTENCES = re.compile(r"(?<=[.!?])\s+")

# (pattern between the two entity mentions, relation type, requires types)
_CUES: list[tuple[re.Pattern[str], str, tuple[str, str]]] = [
    (re.compile(r"\breports?\s+to\b", re.I), "REPORTS_TO", ("person", "person")),
    (re.compile(r"\b(?:works?|working)\s+(?:in|for|at)\b|\bjoined\b|\bmember\s+of\b", re.I),
     "WORKS_IN", ("person", "department")),
    (re.compile(r"\b(?:works?|working)\s+(?:for|at)\b|\bjoined\b|\bemployed\s+by\b", re.I),
     "EMPLOYED_BY", ("person", "organization")),
    (re.compile(r"\b(?:heads?|leads?|manages?|head\s+of)\b", re.I),
     "MANAGES", ("person", "department")),
    (re.compile(r"\bsigned\b|\bapproved\b|\bauthorized\b", re.I),
     "APPROVED", ("person", "money")),
]

_GENERIC = "CO_OCCURS"
# Generic co-occurrence is only worth an edge between these type pairs.
_GENERIC_PAIRS = {
    frozenset({"person", "organization"}),
    frozenset({"person", "department"}),
    frozenset({"organization", "department"}),
    frozenset({"person", "person"}),
}


@dataclass
class Relation:
    source_key: str
    target_key: str
    type: str
    evidence: str
    source_document: str = ""

    @property
    def key(self) -> str:
        return f"{self.source_key}|{self.type}|{self.target_key}"


class RelationDetector:
    def detect(
        self, text: str, entities: list[Entity], source_document: str = ""
    ) -> list[Relation]:
        relations: dict[str, Relation] = {}
        for sentence in _SENTENCES.split(text):
            present = [
                (e, sentence.lower().find(e.text.lower()))
                for e in entities
                if e.text.lower() in sentence.lower()
            ]
            present = [(e, pos) for e, pos in present if pos >= 0]
            present.sort(key=lambda pair: pair[1])

            for i, (a, pos_a) in enumerate(present):
                for b, pos_b in present[i + 1 :]:
                    if a.key == b.key:
                        continue
                    between = sentence[pos_a + len(a.text) : pos_b]
                    relation = self._classify(a, b, between)
                    if relation is None:
                        continue
                    rel = Relation(
                        source_key=a.key,
                        target_key=b.key,
                        type=relation,
                        evidence=sentence.strip()[:300],
                        source_document=source_document,
                    )
                    relations.setdefault(rel.key, rel)
        return list(relations.values())

    @staticmethod
    def _classify(a: Entity, b: Entity, between: str) -> str | None:
        for pattern, rel_type, (src_type, dst_type) in _CUES:
            if a.type == src_type and b.type == dst_type and pattern.search(between):
                return rel_type
        if frozenset({a.type, b.type}) in _GENERIC_PAIRS:
            return _GENERIC
        return None
