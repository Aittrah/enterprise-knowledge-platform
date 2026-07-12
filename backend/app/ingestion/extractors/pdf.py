"""PDF extraction via pypdf (native text layer only; scanned PDFs are

routed to the OCR pipeline in Milestone 5)."""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader

from app.ingestion.extractors.base import BaseExtractor, ExtractionError
from app.ingestion.models import ElementType, ExtractedDocument, ExtractedElement


class PdfExtractor(BaseExtractor):
    extensions = (".pdf",)
    file_type = "pdf"

    def extract(self, path: Path) -> ExtractedDocument:
        doc = self._new_document(path)
        try:
            reader = PdfReader(path)
        except Exception as exc:  # pypdf raises many concrete types
            raise ExtractionError(f"Cannot open PDF {path.name}: {exc}") from exc

        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception as exc:
                raise ExtractionError(f"PDF {path.name} is password-protected") from exc

        info = reader.metadata
        if info:
            doc.native_properties = {
                k.lstrip("/").lower(): str(v) for k, v in info.items() if v
            }

        doc.page_count = len(reader.pages)
        empty_pages = 0
        for page_no, page in enumerate(reader.pages, start=1):
            try:
                text = page.extract_text() or ""
            except Exception as exc:
                doc.warnings.append(f"page {page_no}: extraction failed ({exc})")
                continue
            text = text.strip()
            if not text:
                empty_pages += 1
                continue
            doc.elements.append(
                ExtractedElement(ElementType.PARAGRAPH, text, position=page_no)
            )

        if doc.page_count and empty_pages == doc.page_count:
            doc.warnings.append(
                "no text layer found on any page — document is likely scanned; route to OCR"
            )
        return doc
