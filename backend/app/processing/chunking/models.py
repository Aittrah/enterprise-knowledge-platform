"""Chunk model."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Chunk:
    """One retrieval unit. ``metadata`` travels with the chunk into the

    vector store and is what citations resolve against."""

    text: str
    index: int
    token_count: int
    metadata: dict[str, Any] = field(default_factory=dict)
    # Chunks that must not be split further or size-flagged (whole tables).
    keep_whole: bool = False

    @property
    def id(self) -> str:
        """Deterministic id: same source + strategy + position + content
        always produces the same id, so re-ingestion upserts cleanly."""
        seed = ":".join(
            [
                str(self.metadata.get("source", "")),
                str(self.metadata.get("strategy", "")),
                str(self.index),
                hashlib.blake2b(self.text.encode(), digest_size=8).hexdigest(),
            ]
        )
        return hashlib.blake2b(seed.encode(), digest_size=16).hexdigest()
