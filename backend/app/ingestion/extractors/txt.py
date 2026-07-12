"""Plain-text extraction with encoding detection (charset-normalizer)."""

from __future__ import annotations

from pathlib import Path

from charset_normalizer import from_bytes

from app.ingestion.extractors.base import BaseExtractor, ExtractionError
from app.ingestion.models import ElementType, ExtractedDocument, ExtractedElement


class TxtExtractor(BaseExtractor):
    extensions = (".txt", ".md", ".log")
    file_type = "txt"

    def extract(self, path: Path) -> ExtractedDocument:
        doc = self._new_document(path)
        raw = path.read_bytes()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            best = from_bytes(raw).best()
            if best is None:
                raise ExtractionError(f"Cannot detect encoding of {path.name}")
            text = str(best)
            doc.warnings.append(f"decoded as {best.encoding} (not utf-8)")

        # Blank-line separated blocks keep paragraph structure for chunking.
        for block in text.replace("\r\n", "\n").split("\n\n"):
            block = block.strip()
            if block:
                doc.elements.append(ExtractedElement(ElementType.PARAGRAPH, block))
        return doc
