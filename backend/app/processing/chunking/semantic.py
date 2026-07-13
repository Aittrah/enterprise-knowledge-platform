"""Semantic chunking: structure- and topic-aware grouping of extracted

elements.

Boundaries come from three signals, in priority order:
  1. headings           — a heading always starts a new chunk and updates
                          the breadcrumb (heading path) carried in metadata
  2. tables             — kept whole, one chunk each, never split
  3. topic shift        — consecutive prose with low lexical cohesion
                          splits once the current chunk has enough content

Cohesion is Jaccard overlap of content words. It is deliberately a
pluggable callable: at Milestone 8 an embedding-cosine function replaces
the lexical default without touching this module's logic.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field

from app.ingestion.models import ElementType, ExtractedDocument, ExtractedElement
from app.processing.chunking.recursive import RecursiveChunker
from app.processing.chunking.tokens import DEFAULT_COUNTER, TokenCounter

_WORDS = re.compile(r"[a-z]{3,}")
_STOPWORDS = frozenset(
    "the and for are but not you all any can had her was one our out day get has him "
    "his how man new now old see two way who its did yet with this that from they "
    "have will your which their there been more when were what said each she may use "
    "than them these some would other into only could most also after first".split()
)


def lexical_cohesion(a: str, b: str) -> float:
    """Jaccard overlap of content words — the default topic-shift signal."""
    words_a = {w for w in _WORDS.findall(a.lower()) if w not in _STOPWORDS}
    words_b = {w for w in _WORDS.findall(b.lower()) if w not in _STOPWORDS}
    if not words_a or not words_b:
        return 1.0  # no evidence of a shift
    return len(words_a & words_b) / len(words_a | words_b)


_HEADING_TYPES = frozenset({ElementType.HEADING, ElementType.SLIDE_TITLE})


@dataclass
class ElementGroup:
    """A chunk-in-progress: elements plus the heading path they live under."""

    elements: list[ExtractedElement] = field(default_factory=list)
    heading_path: tuple[str, ...] = ()
    keep_whole: bool = False  # tables: never split, never size-flagged

    @property
    def headings_only(self) -> bool:
        return bool(self.elements) and all(
            e.type in _HEADING_TYPES for e in self.elements
        )

    @property
    def text(self) -> str:
        return "\n\n".join(e.text for e in self.elements)

    @property
    def pages(self) -> list[int]:
        return sorted({e.position for e in self.elements if e.position is not None})

    @property
    def element_types(self) -> list[str]:
        return sorted({e.type.value for e in self.elements})


class SemanticChunker:
    name = "semantic"

    def __init__(
        self,
        max_tokens: int = 512,
        min_tokens: int = 64,
        cohesion_threshold: float = 0.08,
        cohesion: Callable[[str, str], float] = lexical_cohesion,
        counter: TokenCounter = DEFAULT_COUNTER,
    ) -> None:
        self.max_tokens = max_tokens
        self.min_tokens = min_tokens
        self.cohesion_threshold = cohesion_threshold
        self.cohesion = cohesion
        self.counter = counter
        self._fallback = RecursiveChunker(max_tokens=max_tokens, counter=counter)

    def group(self, document: ExtractedDocument) -> list[ElementGroup]:
        groups: list[ElementGroup] = []
        current = ElementGroup()
        heading_path: list[str] = []

        def flush() -> None:
            nonlocal current
            if current.elements:
                groups.append(current)
            current = ElementGroup(heading_path=tuple(heading_path))

        for element in document.elements:
            if element.type in _HEADING_TYPES:
                # A run of consecutive headings stays together; anything
                # else flushes so the heading opens a fresh chunk.
                if current.elements and not current.headings_only:
                    flush()
                level = element.extra.get("level", 1)
                del heading_path[max(0, level - 1) :]
                heading_path.append(element.text)
                current.elements.append(element)
                current.heading_path = tuple(heading_path)
                continue

            if element.type is ElementType.TABLE:
                if current.headings_only:
                    # "## Fees" directly above a table belongs with it.
                    current.elements.append(element)
                    current.keep_whole = True
                    flush()
                else:
                    flush()
                    groups.append(
                        ElementGroup(
                            elements=[element],
                            heading_path=tuple(heading_path),
                            keep_whole=True,
                        )
                    )
                continue

            if current.elements and not current.headings_only:
                over_budget = (
                    self.counter.count(current.text) + self.counter.count(element.text)
                    > self.max_tokens
                )
                last_prose = current.elements[-1]
                topic_shift = (
                    last_prose.type not in _HEADING_TYPES
                    and self.counter.count(current.text) >= self.min_tokens
                    and self.cohesion(last_prose.text, element.text)
                    < self.cohesion_threshold
                )
                if over_budget or topic_shift:
                    flush()
            current.elements.append(element)

        flush()
        return groups

    def split_oversized(self, group: ElementGroup) -> list[str]:
        """Prose groups that still exceed the budget fall back to recursive
        splitting; tables are exempt (kept whole)."""
        return self._fallback.split(group.text)
