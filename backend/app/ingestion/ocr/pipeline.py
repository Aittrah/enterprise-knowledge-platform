"""OCR pipeline: image/scanned-PDF -> preprocess -> recognize -> layout ->

paragraph/table elements with confidence, plus receipt fields."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from app.ingestion.models import ElementType, ExtractedDocument, ExtractedElement
from app.ingestion.ocr.engine import OcrEngine, TesseractEngine
from app.ingestion.ocr.fields import extract_receipt_fields
from app.ingestion.ocr.layout import group_blocks, group_lines
from app.ingestion.ocr.preprocess import preprocess
from app.ingestion.ocr.tables import table_text

IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp")

_LOW_CONFIDENCE = 60.0


class OcrPipeline:
    def __init__(self, engine: OcrEngine | None = None, dpi: int = 200) -> None:
        self.engine = engine or TesseractEngine()
        self._dpi = dpi

    def available(self) -> bool:
        return self.engine.is_available()

    def ocr(self, path: Path | str) -> ExtractedDocument:
        path = Path(path)
        if path.suffix.lower() == ".pdf":
            return self.ocr_pdf(path)
        return self.ocr_image(path)

    def ocr_image(self, path: Path) -> ExtractedDocument:
        doc = ExtractedDocument(source_path=str(path), file_type="image")
        with Image.open(path) as img:
            self._ocr_page(img, doc, page_no=None)
        doc.page_count = 1
        self._finalize(doc)
        return doc

    def ocr_pdf(self, path: Path) -> ExtractedDocument:
        from app.ingestion.ocr.pdf_render import render_pdf_pages

        doc = ExtractedDocument(source_path=str(path), file_type="pdf")
        pages = 0
        for page_no, image in render_pdf_pages(path, dpi=self._dpi):
            pages = page_no
            self._ocr_page(image, doc, page_no=page_no)
        doc.page_count = pages
        self._finalize(doc)
        return doc

    def _ocr_page(
        self, image: Image.Image, doc: ExtractedDocument, page_no: int | None
    ) -> None:
        words = self.engine.recognize(preprocess(image))
        if not words:
            doc.warnings.append(
                f"page {page_no or 1}: no text recognized"
            )
            return

        for block in group_blocks(group_lines(words)):
            confidences = [w.confidence for line in block.lines for w in line.words]
            confidence = round(sum(confidences) / len(confidences), 1)
            if block.kind == "table":
                element = ExtractedElement(
                    ElementType.TABLE,
                    table_text(block),
                    position=page_no,
                    extra={"confidence": confidence, "columns": block.extra.get("columns")},
                )
            else:
                element = ExtractedElement(
                    ElementType.PARAGRAPH,
                    block.text,
                    position=page_no,
                    extra={"confidence": confidence},
                )
            if confidence < _LOW_CONFIDENCE:
                doc.warnings.append(
                    f"page {page_no or 1}: low-confidence block ({confidence:.0f}%)"
                )
            doc.elements.append(element)

    def _finalize(self, doc: ExtractedDocument) -> None:
        doc.native_properties["ocr_engine"] = self.engine.name
        confidences = [
            e.extra["confidence"] for e in doc.elements if "confidence" in e.extra
        ]
        if confidences:
            doc.native_properties["ocr_confidence"] = round(
                sum(confidences) / len(confidences), 1
            )
        fields = extract_receipt_fields(doc.text)
        if fields:
            doc.native_properties["receipt_fields"] = fields
