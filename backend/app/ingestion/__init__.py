"""Document ingestion: extractors, metadata generation, version tracking.

Public API:
    IngestionPipeline  — orchestrates extract -> metadata -> version
    extract            — run the right extractor for a file
    UnsupportedFormatError
"""

from app.ingestion.extractors import UnsupportedFormatError, extract
from app.ingestion.pipeline import IngestionPipeline, IngestionResult

__all__ = ["IngestionPipeline", "IngestionResult", "UnsupportedFormatError", "extract"]
