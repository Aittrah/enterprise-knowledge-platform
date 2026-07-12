from pathlib import Path

from app.ingestion import IngestionPipeline


def test_end_to_end_ingestion(tmp_path: Path, sample_txt: Path):
    pipeline = IngestionPipeline(tmp_path / "versions.json")
    result = pipeline.ingest(sample_txt)

    assert "22 days of annual leave" in result.document.text
    assert result.metadata.sha256
    assert result.metadata.extra["version"] == 1
    assert result.version.version == 1
    assert not result.skipped_duplicate


def test_reingesting_same_bytes_is_flagged_duplicate(tmp_path: Path, sample_txt: Path):
    pipeline = IngestionPipeline(tmp_path / "versions.json")
    pipeline.ingest(sample_txt)
    result = pipeline.ingest(sample_txt)
    assert result.skipped_duplicate


def test_modified_file_becomes_version_two(tmp_path: Path, sample_txt: Path):
    pipeline = IngestionPipeline(tmp_path / "versions.json")
    pipeline.ingest(sample_txt)

    sample_txt.write_text("Leave Policy\n\nNow 25 days of annual leave.", encoding="utf-8")
    result = pipeline.ingest(sample_txt)

    assert result.version.version == 2
    assert result.version.is_new_version
    assert len(pipeline.history(sample_txt.name)) == 2
