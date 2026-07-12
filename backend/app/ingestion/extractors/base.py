"""Extractor contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from app.ingestion.models import ExtractedDocument


class ExtractionError(Exception):
    """Raised when a file cannot be parsed by its extractor."""


class BaseExtractor(ABC):
    """One extractor per family of file formats."""

    #: lowercase extensions (with dot) this extractor handles
    extensions: tuple[str, ...] = ()
    file_type: str = ""

    @abstractmethod
    def extract(self, path: Path) -> ExtractedDocument:
        """Parse *path* into structured elements. Must not raise for
        recoverable issues — record them in ``ExtractedDocument.warnings``."""

    def _new_document(self, path: Path) -> ExtractedDocument:
        return ExtractedDocument(source_path=str(path), file_type=self.file_type)
