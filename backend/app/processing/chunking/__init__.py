"""Chunking engine: turn a cleaned ``ExtractedDocument`` into retrieval-

ready chunks.

Strategies:
    token      — fixed-size sliding window with overlap (baseline)
    recursive  — separator hierarchy (paragraph > line > sentence > word)
    semantic   — structure-aware: heading boundaries, whole tables,
                 lexical-cohesion topic breaks (default)

Every chunk carries provenance metadata (heading path, pages, element
types) — the "metadata chunking" requirement — and a deterministic id.
"""

from app.processing.chunking.generator import ChunkGenerator
from app.processing.chunking.models import Chunk
from app.processing.chunking.validator import ChunkValidator, ValidationReport

__all__ = ["Chunk", "ChunkGenerator", "ChunkValidator", "ValidationReport"]
