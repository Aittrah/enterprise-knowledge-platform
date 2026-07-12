"""Ingestion pipeline: extract -> metadata -> version registration.

Cleaning (M6), chunking (M7), and embedding (M8) attach after this stage.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.ingestion.extractors import extract
from app.ingestion.metadata import generate_metadata
from app.ingestion.models import DocumentMetadata, ExtractedDocument, VersionInfo
from app.ingestion.versioning import VersionTracker


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
    def __init__(self, version_store: Path) -> None:
        self._versions = VersionTracker(version_store)

    def ingest(self, path: Path | str, document_key: str | None = None) -> IngestionResult:
        path = Path(path)
        document = extract(path)
        metadata = generate_metadata(path, document)
        version = self._versions.register(document_key or path.name, metadata.sha256)
        metadata.extra["version"] = version.version
        return IngestionResult(document=document, metadata=metadata, version=version)

    def history(self, document_key: str) -> list[dict]:
        return self._versions.history(document_key)
