"""Data models shared across the ingestion pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class ElementType(str, Enum):
    """Structural role of an extracted piece of content."""

    HEADING = "heading"
    PARAGRAPH = "paragraph"
    TABLE = "table"
    LIST_ITEM = "list_item"
    SLIDE_TITLE = "slide_title"
    SLIDE_BODY = "slide_body"
    SPEAKER_NOTES = "speaker_notes"
    ROW = "row"


@dataclass
class ExtractedElement:
    """One unit of content with enough structure for downstream chunking."""

    type: ElementType
    text: str
    # 1-based page (PDF), slide (PPTX) or row (CSV) index when the format has one.
    position: int | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractedDocument:
    """Full extraction result for a single source file."""

    source_path: str
    file_type: str
    elements: list[ExtractedElement] = field(default_factory=list)
    # Document properties reported by the format itself (PDF info, DOCX core props, <title>).
    native_properties: dict[str, Any] = field(default_factory=dict)
    page_count: int | None = None
    warnings: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        """Plain-text view of the whole document."""
        return "\n\n".join(e.text for e in self.elements if e.text.strip())

    @property
    def tables(self) -> list[ExtractedElement]:
        return [e for e in self.elements if e.type is ElementType.TABLE]


@dataclass
class DocumentMetadata:
    """System + native metadata persisted alongside a document."""

    filename: str
    file_type: str
    size_bytes: int
    sha256: str
    mime_type: str | None
    title: str | None = None
    author: str | None = None
    page_count: int | None = None
    element_count: int = 0
    modified_at: datetime | None = None
    ingested_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tags: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class VersionInfo:
    """Outcome of registering a document with the version tracker."""

    document_key: str
    version: int
    sha256: str
    ingested_at: str
    is_new_version: bool
    is_duplicate: bool
