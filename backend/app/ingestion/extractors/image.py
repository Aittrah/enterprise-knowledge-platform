"""Image extraction = OCR. Photos of receipts, invoices, and scans enter

the same ingestion pipeline as native documents."""

from __future__ import annotations

from pathlib import Path

from app.ingestion.extractors.base import BaseExtractor, ExtractionError
from app.ingestion.models import ExtractedDocument
from app.ingestion.ocr.pipeline import IMAGE_EXTENSIONS, OcrPipeline


class ImageExtractor(BaseExtractor):
    extensions = IMAGE_EXTENSIONS
    file_type = "image"

    def __init__(self, ocr: OcrPipeline | None = None) -> None:
        self._ocr = ocr or OcrPipeline()

    def extract(self, path: Path) -> ExtractedDocument:
        if not self._ocr.available():
            raise ExtractionError(
                f"Cannot OCR {path.name}: the '{self._ocr.engine.name}' engine is not "
                "installed. On Windows install Tesseract from "
                "https://github.com/UB-Mannheim/tesseract/wiki or `choco install tesseract`."
            )
        return self._ocr.ocr_image(path)
