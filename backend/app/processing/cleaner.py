"""Cleaning pipeline: normalize -> strip page chrome -> drop boilerplate ->

deduplicate elements within the document. Runs in place on an
``ExtractedDocument`` and records what it did in ``native_properties``.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass

from app.ingestion.models import ElementType, ExtractedDocument
from app.processing.dedup import DeduplicationEngine
from app.processing.headers_footers import strip_headers_footers
from app.processing.normalize import normalize_text

# Whole elements that carry no content: bare page markers, separators.
_BOILERPLATE = (
    re.compile(r"^page \d+( of \d+)?$", re.I),
    re.compile(r"^\d+ ?/ ?\d+$"),
    re.compile(r"^[-_=*.·•\s]+$"),
    re.compile(r"^(confidential|draft|internal use only)$", re.I),
)

# Structured rows repeat legitimately (CSV/table data), so they are only
# deduplicated on exact content, never on near-similarity.
_NEAR_DEDUP_TYPES = frozenset({ElementType.PARAGRAPH, ElementType.LIST_ITEM})


@dataclass
class CleaningStats:
    elements_in: int = 0
    elements_out: int = 0
    chrome_lines_removed: int = 0
    boilerplate_dropped: int = 0
    exact_duplicates_dropped: int = 0
    near_duplicates_dropped: int = 0


class CleaningPipeline:
    def __init__(self, near_threshold: float = 0.92, dedupe: bool = True) -> None:
        self._near_threshold = near_threshold
        self._dedupe = dedupe

    def clean(self, document: ExtractedDocument) -> CleaningStats:
        stats = CleaningStats(elements_in=len(document.elements))

        for element in document.elements:
            element.text = normalize_text(element.text)
        document.elements = [e for e in document.elements if e.text]

        stats.chrome_lines_removed = strip_headers_footers(document)

        kept = []
        for element in document.elements:
            if any(p.match(element.text.strip()) for p in _BOILERPLATE):
                stats.boilerplate_dropped += 1
            else:
                kept.append(element)
        document.elements = kept

        if self._dedupe:
            self._dedupe_elements(document, stats)

        stats.elements_out = len(document.elements)
        document.native_properties["cleaning"] = asdict(stats)
        return stats

    def _dedupe_elements(self, document: ExtractedDocument, stats: CleaningStats) -> None:
        engine = DeduplicationEngine(near_threshold=self._near_threshold)
        kept = []
        for index, element in enumerate(document.elements):
            match = engine.check(element.text)
            if match is not None and match.kind == "exact":
                stats.exact_duplicates_dropped += 1
                continue
            if (
                match is not None
                and match.kind == "near"
                and element.type in _NEAR_DEDUP_TYPES
            ):
                stats.near_duplicates_dropped += 1
                continue
            engine.add(f"element-{index}", element.text)
            kept.append(element)
        document.elements = kept
