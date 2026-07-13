"""Repeated header/footer removal for paginated documents.

Lines that recur at the top or bottom edge of most pages ("ACME Corp -
Confidential", "Page 3 of 12") are chrome, not content. Detection uses a
digit-masked fingerprint so page counters register as the same line.
"""

from __future__ import annotations

import re
from collections import Counter
from math import ceil

from app.ingestion.models import ExtractedDocument

# How many lines at each page edge are header/footer candidates.
_EDGE_LINES = 2
# A fingerprint must appear on at least this share of pages, and on at
# least _MIN_PAGES pages, to be treated as chrome.
_PAGE_SHARE = 0.6
_MIN_PAGES = 3

_DIGITS = re.compile(r"\d+")
# Chrome lines are short; long edge lines are body text that happens to sit
# at a page boundary and must never be treated as chrome.
_MAX_CHROME_LENGTH = 80


def _fingerprint(line: str) -> str:
    return _DIGITS.sub("#", line.strip().lower())


def _pages(document: ExtractedDocument) -> dict[int, list[str]]:
    pages: dict[int, list[str]] = {}
    for element in document.elements:
        if element.position is None:
            continue
        pages.setdefault(element.position, []).extend(
            line for line in element.text.split("\n") if line.strip()
        )
    return pages


def detect_chrome_lines(document: ExtractedDocument) -> set[str]:
    """Fingerprints of lines that repeat at page edges across the document."""
    pages = _pages(document)
    if len(pages) < _MIN_PAGES:
        return set()

    counts: Counter[str] = Counter()
    for lines in pages.values():
        edge = lines[:_EDGE_LINES] + lines[-_EDGE_LINES:]
        candidates = {
            _fingerprint(line)
            for line in edge
            if line.strip() and len(line.strip()) <= _MAX_CHROME_LENGTH
        }
        for fp in candidates:
            counts[fp] += 1

    needed = max(_MIN_PAGES, ceil(_PAGE_SHARE * len(pages)))
    return {fp for fp, count in counts.items() if count >= needed}


def strip_headers_footers(document: ExtractedDocument) -> int:
    """Remove detected chrome lines everywhere in the document.

    Returns the number of lines removed. Elements left empty are dropped.
    """
    chrome = detect_chrome_lines(document)
    if not chrome:
        return 0

    removed = 0
    kept_elements = []
    for element in document.elements:
        lines = element.text.split("\n")
        kept = [line for line in lines if _fingerprint(line) not in chrome]
        removed += len(lines) - len(kept)
        element.text = "\n".join(kept).strip()
        if element.text:
            kept_elements.append(element)
    document.elements = kept_elements
    return removed
