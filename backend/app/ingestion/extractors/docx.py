"""DOCX extraction via python-docx: paragraphs with heading levels, tables,

and core document properties."""

from __future__ import annotations

from pathlib import Path

import docx
from docx.document import Document as DocxDocument
from docx.table import Table
from docx.text.paragraph import Paragraph

from app.ingestion.extractors.base import BaseExtractor, ExtractionError
from app.ingestion.models import ElementType, ExtractedDocument, ExtractedElement


def _iter_blocks(document: DocxDocument):
    """Yield paragraphs and tables in true document order."""
    from docx.oxml.table import CT_Tbl
    from docx.oxml.text.paragraph import CT_P

    for child in document.element.body.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, document)
        elif isinstance(child, CT_Tbl):
            yield Table(child, document)


def _table_to_text(table: Table) -> str:
    rows = []
    for row in table.rows:
        cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
        rows.append(" | ".join(cells))
    return "\n".join(rows)


class DocxExtractor(BaseExtractor):
    extensions = (".docx",)
    file_type = "docx"

    def extract(self, path: Path) -> ExtractedDocument:
        doc = self._new_document(path)
        try:
            source = docx.Document(str(path))
        except Exception as exc:
            raise ExtractionError(f"Cannot open DOCX {path.name}: {exc}") from exc

        props = source.core_properties
        doc.native_properties = {
            "title": props.title or None,
            "author": props.author or None,
            "created": props.created.isoformat() if props.created else None,
            "modified": props.modified.isoformat() if props.modified else None,
        }

        for block in _iter_blocks(source):
            if isinstance(block, Paragraph):
                text = block.text.strip()
                if not text:
                    continue
                style = (block.style.name or "").lower() if block.style else ""
                if style.startswith("heading") or style == "title":
                    level = int(style.split()[-1]) if style[-1].isdigit() else 1
                    doc.elements.append(
                        ExtractedElement(
                            ElementType.HEADING, text, extra={"level": level}
                        )
                    )
                elif style.startswith("list"):
                    doc.elements.append(ExtractedElement(ElementType.LIST_ITEM, text))
                else:
                    doc.elements.append(ExtractedElement(ElementType.PARAGRAPH, text))
            else:  # Table
                text = _table_to_text(block)
                if text.strip():
                    doc.elements.append(
                        ExtractedElement(
                            ElementType.TABLE,
                            text,
                            extra={"rows": len(block.rows), "cols": len(block.columns)},
                        )
                    )
        return doc
