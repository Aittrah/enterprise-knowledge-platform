"""Ingestion pipeline: extract -> OCR fallback -> clean -> metadata ->

version registration. Chunking (M7) and embedding (M8) attach after this.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.ingestion.extractors import extract
from app.ingestion.metadata import generate_metadata
from app.ingestion.models import DocumentMetadata, ExtractedDocument, VersionInfo
from app.ingestion.ocr.pipeline import OcrPipeline
from app.ingestion.versioning import VersionTracker
from app.processing.cleaner import CleaningPipeline


@dataclass
class IngestionResult:
    document: ExtractedDocument
    metadata: DocumentMetadata
    version: VersionInfo

    @property
    def skipped_duplicate(self) -> bool:
        """True when identical content was already ingested for this key."""
        return self.version.is_duplicate


class IngestionPipeline:
    def __init__(
        self,
        version_store: Path,
        ocr: OcrPipeline | None = None,
        ocr_scanned_pdfs: bool = True,
        cleaner: CleaningPipeline | None = None,
        clean: bool = True,
    ) -> None:
        self._versions = VersionTracker(version_store)
        self._ocr = ocr or OcrPipeline()
        self._ocr_scanned_pdfs = ocr_scanned_pdfs
        self._cleaner = cleaner or CleaningPipeline()
        self._clean = clean

    def ingest(self, path: Path | str, document_key: str | None = None) -> IngestionResult:
        path = Path(path)
        document = extract(path)
        if self._ocr_scanned_pdfs and any("route to OCR" in w for w in document.warnings):
            document = self._recover_scanned_pdf(path, document)
        if self._clean:
            self._cleaner.clean(document)
        metadata = generate_metadata(path, document)
        version = self._versions.register(document_key or path.name, metadata.sha256)
        metadata.extra["version"] = version.version
        return IngestionResult(document=document, metadata=metadata, version=version)

    def history(self, document_key: str) -> list[dict]:
        return self._versions.history(document_key)

    def _recover_scanned_pdf(
        self, path: Path, document: ExtractedDocument
    ) -> ExtractedDocument:
        if not self._ocr.available():
            document.warnings.append(
                f"OCR engine '{self._ocr.engine.name}' unavailable; scanned text not recovered"
            )
            return document
        recovered = self._ocr.ocr_pdf(path)
        recovered.warnings = [*document.warnings, "text recovered via OCR"]
        return recovered
