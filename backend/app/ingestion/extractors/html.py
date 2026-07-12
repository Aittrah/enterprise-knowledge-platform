"""HTML extraction via BeautifulSoup: headings, paragraphs, list items,

tables; scripts/styles/nav chrome stripped."""

from __future__ import annotations

from pathlib import Path

from bs4 import BeautifulSoup

from app.ingestion.extractors.base import BaseExtractor
from app.ingestion.models import ElementType, ExtractedDocument, ExtractedElement

_SKIP_TAGS = ("script", "style", "noscript", "nav", "footer", "header", "aside")
_HEADINGS = ("h1", "h2", "h3", "h4", "h5", "h6")


class HtmlExtractor(BaseExtractor):
    extensions = (".html", ".htm")
    file_type = "html"

    def extract(self, path: Path) -> ExtractedDocument:
        doc = self._new_document(path)
        soup = BeautifulSoup(path.read_bytes(), "lxml")

        if soup.title and soup.title.string:
            doc.native_properties["title"] = soup.title.string.strip()

        for tag in soup.find_all(_SKIP_TAGS):
            tag.decompose()

        body = soup.body or soup
        for tag in body.find_all([*_HEADINGS, "p", "li", "table"]):
            if tag.name == "table":
                rows = []
                for tr in tag.find_all("tr"):
                    cells = [
                        td.get_text(" ", strip=True) for td in tr.find_all(["td", "th"])
                    ]
                    if any(cells):
                        rows.append(" | ".join(cells))
                if rows:
                    doc.elements.append(
                        ExtractedElement(
                            ElementType.TABLE, "\n".join(rows), extra={"rows": len(rows)}
                        )
                    )
                continue
            if tag.find_parent("table"):
                continue  # cells already captured by the table above
            text = tag.get_text(" ", strip=True)
            if not text:
                continue
            if tag.name in _HEADINGS:
                doc.elements.append(
                    ExtractedElement(
                        ElementType.HEADING, text, extra={"level": int(tag.name[1])}
                    )
                )
            elif tag.name == "li":
                doc.elements.append(ExtractedElement(ElementType.LIST_ITEM, text))
            else:
                doc.elements.append(ExtractedElement(ElementType.PARAGRAPH, text))
        return doc
