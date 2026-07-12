import hashlib
from pathlib import Path

from app.ingestion.extractors import extract
from app.ingestion.metadata import generate_metadata, sha256_file


def test_sha256_matches_hashlib(sample_txt: Path):
    expected = hashlib.sha256(sample_txt.read_bytes()).hexdigest()
    assert sha256_file(sample_txt) == expected


def test_metadata_fields(sample_docx: Path):
    doc = extract(sample_docx)
    meta = generate_metadata(sample_docx, doc)
    assert meta.filename == "report.docx"
    assert meta.file_type == "docx"
    assert meta.size_bytes == sample_docx.stat().st_size
    assert meta.title == "Q3 Financial Report"  # native property wins
    assert meta.author == "Finance Team"
    assert meta.element_count == len(doc.elements)
    assert meta.mime_type and "wordprocessingml" in meta.mime_type
    assert meta.ingested_at.tzinfo is not None


def test_metadata_title_falls_back_to_stem(sample_txt: Path):
    meta = generate_metadata(sample_txt, extract(sample_txt))
    assert meta.title == "policy"
