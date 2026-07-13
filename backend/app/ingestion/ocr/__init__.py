"""OCR pipeline: scanned PDFs, images, receipts and invoices.

The engine (Tesseract by default) only produces positioned words; layout
detection, table reconstruction and field extraction are engine-agnostic
and run on word geometry.
"""

from app.ingestion.ocr.engine import OcrEngine, OcrEngineUnavailableError, OcrWord, TesseractEngine
from app.ingestion.ocr.fields import extract_receipt_fields
from app.ingestion.ocr.pipeline import OcrPipeline

__all__ = [
    "OcrEngine",
    "OcrEngineUnavailableError",
    "OcrPipeline",
    "OcrWord",
    "TesseractEngine",
    "extract_receipt_fields",
]
