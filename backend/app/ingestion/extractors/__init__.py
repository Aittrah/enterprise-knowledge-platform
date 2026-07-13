"""Extractor registry: pick the right extractor by file extension."""

from __future__ import annotations

from pathlib import Path

from app.ingestion.extractors.base import BaseExtractor, ExtractionError
from app.ingestion.extractors.csv import CsvExtractor
from app.ingestion.extractors.docx import DocxExtractor
from app.ingestion.extractors.html import HtmlExtractor
from app.ingestion.extractors.image import ImageExtractor
from app.ingestion.extractors.pdf import PdfExtractor
from app.ingestion.extractors.pptx import PptxExtractor
from app.ingestion.extractors.txt import TxtExtractor
from app.ingestion.models import ExtractedDocument


class UnsupportedFormatError(Exception):
    """The file extension has no registered extractor."""


_EXTRACTOR_CLASSES: tuple[type[BaseExtractor], ...] = (
    PdfExtractor,
    DocxExtractor,
    TxtExtractor,
    HtmlExtractor,
    CsvExtractor,
    PptxExtractor,
    ImageExtractor,
)

_REGISTRY: dict[str, BaseExtractor] = {
    ext: cls() for cls in _EXTRACTOR_CLASSES for ext in cls.extensions
}

SUPPORTED_EXTENSIONS = tuple(sorted(_REGISTRY))


def get_extractor(path: Path | str) -> BaseExtractor:
    ext = Path(path).suffix.lower()
    try:
        return _REGISTRY[ext]
    except KeyError:
        raise UnsupportedFormatError(
            f"No extractor for '{ext}'. Supported: {', '.join(SUPPORTED_EXTENSIONS)}"
        ) from None


def extract(path: Path | str) -> ExtractedDocument:
    """Extract *path* with the extractor registered for its extension."""
    return get_extractor(path).extract(Path(path))


__all__ = [
    "BaseExtractor",
    "ExtractionError",
    "UnsupportedFormatError",
    "SUPPORTED_EXTENSIONS",
    "get_extractor",
    "extract",
]
