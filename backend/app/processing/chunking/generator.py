"""ChunkGenerator: strategy dispatch + metadata enrichment.

Whatever the strategy, every chunk leaves here carrying provenance
(source, title, version, heading path, pages, element types) — this is
the metadata that filters apply to at retrieval (M12) and that citations
resolve against (M15/M20).
"""

from __future__ import annotations

from app.ingestion.models import DocumentMetadata, ExtractedDocument
from app.processing.chunking.models import Chunk
from app.processing.chunking.recursive import RecursiveChunker
from app.processing.chunking.semantic import SemanticChunker
from app.processing.chunking.token_chunker import TokenChunker
from app.processing.chunking.tokens import DEFAULT_COUNTER, TokenCounter

STRATEGIES = ("semantic", "recursive", "token")


class ChunkGenerator:
    def __init__(
        self,
        strategy: str = "semantic",
        max_tokens: int = 512,
        overlap: int = 64,
        min_chunk_tokens: int = 20,
        counter: TokenCounter = DEFAULT_COUNTER,
    ) -> None:
        if strategy not in STRATEGIES:
            raise ValueError(f"Unknown strategy '{strategy}'. Choose from {STRATEGIES}")
        self.strategy = strategy
        self.max_tokens = max_tokens
        self.min_chunk_tokens = min_chunk_tokens
        self.counter = counter
        self._semantic = SemanticChunker(max_tokens=max_tokens, counter=counter)
        self._recursive = RecursiveChunker(max_tokens=max_tokens, counter=counter)
        self._token = TokenChunker(max_tokens=max_tokens, overlap=overlap, counter=counter)

    def generate(
        self, document: ExtractedDocument, metadata: DocumentMetadata | None = None
    ) -> list[Chunk]:
        base = self._base_metadata(document, metadata)
        if self.strategy == "semantic":
            return self._generate_semantic(document, base)

        chunker = self._recursive if self.strategy == "recursive" else self._token
        return [
            self._chunk(text, index, base)
            for index, text in enumerate(chunker.split(document.text))
        ]

    def _generate_semantic(
        self, document: ExtractedDocument, base: dict
    ) -> list[Chunk]:
        pieces: list[tuple[str, dict, bool]] = []
        for group in self._semantic.group(document):
            extra = {
                "heading_path": list(group.heading_path),
                "pages": group.pages,
                "element_types": group.element_types,
            }
            if group.keep_whole or self.counter.count(group.text) <= self._semantic.max_tokens:
                pieces.append((group.text, base | extra, group.keep_whole))
            else:
                for text in self._semantic.split_oversized(group):
                    pieces.append((text, base | extra, False))
        pieces = self._merge_undersized(pieces)
        return [
            self._chunk(text, index, metadata, keep_whole)
            for index, (text, metadata, keep_whole) in enumerate(pieces)
        ]

    def _merge_undersized(
        self, pieces: list[tuple[str, dict, bool]]
    ) -> list[tuple[str, dict, bool]]:
        """Fold fragments below ``min_chunk_tokens`` into a neighbor.

        Slide decks and forms naturally produce tiny groups (a lone slide
        title, a two-word text box); a six-token chunk is useless at
        retrieval time. Tables (keep_whole) are never merge targets."""
        merged: list[tuple[str, dict, bool]] = []
        for text, metadata, keep_whole in pieces:
            tiny = self.counter.count(text) < self.min_chunk_tokens
            can_extend_previous = (
                merged
                and not keep_whole
                and not merged[-1][2]
                and self.counter.count(merged[-1][0]) + self.counter.count(text)
                <= self.max_tokens
            )
            if tiny and can_extend_previous:
                prev_text, prev_meta, _ = merged[-1]
                merged[-1] = (
                    f"{prev_text}\n\n{text}",
                    self._merge_metadata(prev_meta, metadata),
                    False,
                )
            else:
                merged.append((text, metadata, keep_whole))

        # A tiny opening piece has no previous neighbor: fold it forward.
        if (
            len(merged) >= 2
            and not merged[0][2]
            and not merged[1][2]
            and self.counter.count(merged[0][0]) < self.min_chunk_tokens
            and self.counter.count(merged[0][0]) + self.counter.count(merged[1][0])
            <= self.max_tokens
        ):
            first_text, first_meta, _ = merged[0]
            second_text, second_meta, _ = merged[1]
            merged[1] = (
                f"{first_text}\n\n{second_text}",
                self._merge_metadata(first_meta, second_meta),
                False,
            )
            merged.pop(0)
        return merged

    @staticmethod
    def _merge_metadata(base: dict, extra: dict) -> dict:
        combined = dict(base)
        combined["pages"] = sorted(
            {*base.get("pages", []), *extra.get("pages", [])}
        )
        combined["element_types"] = sorted(
            {*base.get("element_types", []), *extra.get("element_types", [])}
        )
        # heading_path stays the earlier piece's — that is where the merged
        # content starts in the document.
        return combined

    def _chunk(
        self, text: str, index: int, metadata: dict, keep_whole: bool = False
    ) -> Chunk:
        return Chunk(
            text=text,
            index=index,
            token_count=self.counter.count(text),
            metadata={"strategy": self.strategy, **metadata},
            keep_whole=keep_whole,
        )

    @staticmethod
    def _base_metadata(
        document: ExtractedDocument, metadata: DocumentMetadata | None
    ) -> dict:
        base = {"source": document.source_path, "file_type": document.file_type}
        if metadata is not None:
            base.update(
                source=metadata.filename,
                title=metadata.title,
                version=metadata.extra.get("version"),
                sha256=metadata.sha256,
            )
        return base
