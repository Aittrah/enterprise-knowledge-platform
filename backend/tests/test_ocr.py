"""OCR pipeline tests.

A fake engine supplies positioned words for a synthetic receipt, so layout
detection, table reconstruction, field extraction, and PDF rendering are all
exercised without the Tesseract binary. A real-Tesseract smoke test runs
only where the binary exists.
"""

from pathlib import Path

import pytest
from PIL import Image

from app.ingestion import IngestionPipeline
from app.ingestion.extractors import get_extractor
from app.ingestion.extractors.base import ExtractionError
from app.ingestion.extractors.image import ImageExtractor
from app.ingestion.models import ElementType
from app.ingestion.ocr import OcrPipeline, OcrWord, TesseractEngine, extract_receipt_fields
from app.ingestion.ocr.layout import group_blocks, group_lines
from app.ingestion.ocr.preprocess import preprocess
from app.ingestion.ocr.tables import block_to_table_rows
from tests.conftest import minimal_pdf


def w(text: str, x0: float, y0: float, x1: float, y1: float, conf: float = 90.0) -> OcrWord:
    return OcrWord(text, x0, y0, x1, y1, conf)


# A receipt: header block (store, receipt no, date) then, after a wide
# vertical gap, an items table (name column at x=10, price column at x=400).
RECEIPT_WORDS = [
    w("ACME", 10, 10, 90, 40),
    w("STORE", 100, 10, 210, 40),
    w("Receipt", 10, 50, 85, 75),
    w("No:", 95, 50, 125, 75),
    w("R-1042", 135, 50, 205, 75),
    w("Date:", 10, 85, 62, 110),
    w("2026-07-13", 72, 85, 185, 110),
    w("Bread", 10, 200, 80, 225),
    w("2.50", 400, 200, 450, 225),
    w("Milk", 10, 235, 60, 260),
    w("3.10", 400, 235, 450, 260),
    w("TOTAL", 10, 270, 80, 295),
    w("5.60", 400, 270, 450, 295),
]


class FakeEngine:
    name = "fake"

    def __init__(self, words=RECEIPT_WORDS):
        self._words = words

    def is_available(self) -> bool:
        return True

    def recognize(self, image) -> list[OcrWord]:
        return list(self._words)


class UnavailableEngine:
    name = "missing"

    def is_available(self) -> bool:
        return False

    def recognize(self, image):
        raise AssertionError("must not be called")


@pytest.fixture
def blank_image(tmp_path: Path) -> Path:
    path = tmp_path / "receipt.png"
    Image.new("RGB", (600, 400), "white").save(path)
    return path


# --- layout -----------------------------------------------------------------


def test_words_group_into_reading_order_lines():
    lines = group_lines(RECEIPT_WORDS)
    assert [line.text for line in lines[:3]] == [
        "ACME STORE",
        "Receipt No: R-1042",
        "Date: 2026-07-13",
    ]


def test_blocks_split_on_vertical_gap_and_classify_tables():
    blocks = group_blocks(group_lines(RECEIPT_WORDS))
    assert len(blocks) == 2
    header, items = blocks
    assert header.kind == "paragraph"
    assert "ACME STORE" in header.text
    assert items.kind == "table"
    assert items.extra["columns"] == 2


def test_table_rows_align_columns():
    items = group_blocks(group_lines(RECEIPT_WORDS))[1]
    assert block_to_table_rows(items) == [
        ["Bread", "2.50"],
        ["Milk", "3.10"],
        ["TOTAL", "5.60"],
    ]


# --- fields -----------------------------------------------------------------


def test_receipt_fields_extraction():
    text = "ACME STORE\nReceipt No: R-1042\nDate: 2026-07-13\nTOTAL | 5.60"
    fields = extract_receipt_fields(text)
    assert fields["invoice_number"] == "R-1042"
    assert fields["date"] == "2026-07-13"
    assert fields["total"] == "5.60"


def test_total_prefers_grand_total_over_item_amounts():
    text = "Subtotal 10.00\nTax 1.50\nTotal 11.50"
    assert extract_receipt_fields(text)["total"] == "11.50"


# --- preprocessing ----------------------------------------------------------


def test_preprocess_binarizes_to_black_and_white():
    img = Image.new("RGB", (2000, 1400), (200, 180, 160))
    out = preprocess(img)
    assert out.mode == "L"
    assert set(out.tobytes()) <= {0, 255}


def test_preprocess_upscales_small_scans():
    out = preprocess(Image.new("L", (400, 300), 255))
    assert max(out.size) >= 1500


# --- pipeline ---------------------------------------------------------------


def test_ocr_image_produces_elements_and_receipt_fields(blank_image: Path):
    doc = OcrPipeline(engine=FakeEngine()).ocr_image(blank_image)
    paragraphs = [e for e in doc.elements if e.type is ElementType.PARAGRAPH]
    tables = [e for e in doc.elements if e.type is ElementType.TABLE]
    assert "ACME STORE" in paragraphs[0].text
    assert tables and "Bread | 2.50" in tables[0].text
    assert doc.native_properties["ocr_engine"] == "fake"
    assert doc.native_properties["ocr_confidence"] == 90.0
    assert doc.native_properties["receipt_fields"]["total"] == "5.60"


def test_ocr_pdf_renders_pages_and_positions_elements(tmp_path: Path):
    pdf = tmp_path / "scan.pdf"
    pdf.write_bytes(minimal_pdf("ignored - fake engine supplies words"))
    doc = OcrPipeline(engine=FakeEngine()).ocr_pdf(pdf)
    assert doc.page_count == 1
    assert all(e.position == 1 for e in doc.elements)


def test_low_confidence_blocks_are_flagged(blank_image: Path):
    shaky = [w("blurry", 10, 10, 80, 40, conf=31.0), w("words", 90, 10, 150, 40, conf=42.0)]
    doc = OcrPipeline(engine=FakeEngine(words=shaky)).ocr_image(blank_image)
    assert any("low-confidence" in warning for warning in doc.warnings)


# --- integration with the ingestion layer -----------------------------------


def test_image_extensions_are_registered():
    assert type(get_extractor("receipt.png")) is ImageExtractor
    assert type(get_extractor("scan.JPG")) is ImageExtractor


def test_image_extraction_without_engine_gives_install_hint(blank_image: Path):
    extractor = ImageExtractor(ocr=OcrPipeline(engine=UnavailableEngine()))
    with pytest.raises(ExtractionError, match="[Tt]esseract"):
        extractor.extract(blank_image)


def test_scanned_pdf_falls_back_to_ocr(tmp_path: Path):
    pdf = tmp_path / "scanned.pdf"
    pdf.write_bytes(minimal_pdf(""))  # valid page, no text layer
    pipeline = IngestionPipeline(
        tmp_path / "versions.json", ocr=OcrPipeline(engine=FakeEngine())
    )
    result = pipeline.ingest(pdf)
    assert "ACME STORE" in result.document.text
    assert any("recovered via OCR" in warning for warning in result.document.warnings)


def test_scanned_pdf_without_engine_keeps_warning(tmp_path: Path):
    pdf = tmp_path / "scanned.pdf"
    pdf.write_bytes(minimal_pdf(""))
    pipeline = IngestionPipeline(
        tmp_path / "versions.json", ocr=OcrPipeline(engine=UnavailableEngine())
    )
    result = pipeline.ingest(pdf)
    assert result.document.text == ""
    assert any("unavailable" in warning for warning in result.document.warnings)


# --- real engine smoke test (runs only where Tesseract is installed) ---------


@pytest.mark.skipif(not TesseractEngine().is_available(), reason="tesseract not installed")
def test_tesseract_reads_rendered_text(tmp_path: Path):
    from PIL import ImageDraw

    img = Image.new("L", (1600, 400), 255)
    draw = ImageDraw.Draw(img)
    draw.text((100, 150), "EKIP OCR TEST 2026", fill=0, font_size=96)
    path = tmp_path / "smoke.png"
    img.save(path)

    doc = OcrPipeline().ocr_image(path)
    assert "EKIP" in doc.text.upper()
