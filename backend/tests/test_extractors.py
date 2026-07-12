from pathlib import Path

import pytest

from app.ingestion.extractors import (
    SUPPORTED_EXTENSIONS,
    UnsupportedFormatError,
    extract,
)
from app.ingestion.models import ElementType


def test_supported_extensions_cover_all_required_formats():
    for ext in (".pdf", ".docx", ".txt", ".html", ".csv", ".pptx"):
        assert ext in SUPPORTED_EXTENSIONS


def test_unsupported_extension_raises(tmp_path: Path):
    exe = tmp_path / "malware.exe"
    exe.write_bytes(b"MZ")
    with pytest.raises(UnsupportedFormatError):
        extract(exe)


def test_txt_extracts_paragraphs(sample_txt: Path):
    doc = extract(sample_txt)
    assert doc.file_type == "txt"
    assert len(doc.elements) == 3
    assert "22 days of annual leave" in doc.text


def test_txt_non_utf8_encoding_is_detected(tmp_path: Path):
    path = tmp_path / "legacy.txt"
    path.write_bytes("Café résumé naïve — legacy encoding".encode("cp1252"))
    doc = extract(path)
    assert "Café" in doc.text
    assert doc.warnings  # decoding fallback recorded


def test_html_extracts_structure_and_skips_scripts(sample_html: Path):
    doc = extract(sample_html)
    assert doc.native_properties["title"] == "Employee Handbook"
    headings = [e for e in doc.elements if e.type is ElementType.HEADING]
    assert headings and headings[0].text == "Benefits"
    assert headings[0].extra["level"] == 1
    assert any(e.type is ElementType.LIST_ITEM for e in doc.elements)
    assert len(doc.tables) == 1
    assert "Plan | Cost" in doc.tables[0].text
    assert "alert" not in doc.text


def test_csv_rows_are_self_describing(sample_csv: Path):
    doc = extract(sample_csv)
    rows = [e for e in doc.elements if e.type is ElementType.ROW]
    assert len(rows) == 2
    assert rows[0].text == "invoice_id: INV-001 | vendor: Acme Corp | amount: 1200.50"
    assert rows[0].position == 2  # line number in the file
    assert doc.native_properties["columns"] == ["invoice_id", "vendor", "amount"]
    assert doc.tables[0].extra["rows"] == 2


def test_docx_headings_tables_and_properties(sample_docx: Path):
    doc = extract(sample_docx)
    assert doc.native_properties["title"] == "Q3 Financial Report"
    assert doc.native_properties["author"] == "Finance Team"
    headings = [e for e in doc.elements if e.type is ElementType.HEADING]
    assert headings[0].text == "Executive Summary"
    assert "Revenue grew 14%" in doc.text
    assert len(doc.tables) == 1
    assert "Revenue | $2.4M" in doc.tables[0].text


def test_pptx_slides_and_notes(sample_pptx: Path):
    doc = extract(sample_pptx)
    assert doc.page_count == 1
    titles = [e for e in doc.elements if e.type is ElementType.SLIDE_TITLE]
    assert titles[0].text == "Platform Overview"
    assert titles[0].position == 1
    notes = [e for e in doc.elements if e.type is ElementType.SPEAKER_NOTES]
    assert notes[0].text == "Mention GraphRAG here"


def test_pdf_text_layer(sample_pdf: Path):
    doc = extract(sample_pdf)
    assert doc.page_count == 1
    assert "Hello EKIP PDF" in doc.text
    assert doc.elements[0].position == 1


def test_pdf_without_text_layer_warns_for_ocr(tmp_path: Path):
    from tests.conftest import minimal_pdf

    # A page whose content stream draws no text.
    blank = minimal_pdf("").replace(b"(", b"% (").replace(b") Tj", b"")
    path = tmp_path / "scanned.pdf"
    path.write_bytes(blank)
    doc = extract(path)
    assert any("OCR" in w for w in doc.warnings)
