"""Post-extraction processing: cleaning, normalization, deduplication.

(Chunking joins this package at Milestone 7.)
"""

from app.processing.cleaner import CleaningPipeline, CleaningStats
from app.processing.dedup import DeduplicationEngine, DuplicateMatch
from app.processing.normalize import normalize_text

__all__ = [
    "CleaningPipeline",
    "CleaningStats",
    "DeduplicationEngine",
    "DuplicateMatch",
    "normalize_text",
]
