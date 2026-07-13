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
        counter: TokenCounter = DEFAULT_COUNTER,
    ) -> None:
        if strategy not in STRATEGIES:
            raise ValueError(f"Unknown strategy '{strategy}'. Choose from {STRATEGIES}")
        self.strategy = strategy
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
        chunks: list[Chunk] = []
        for group in self._semantic.group(document):
            extra = {
                "heading_path": list(group.heading_path),
                "pages": group.pages,
                "element_types": group.element_types,
            }
            if group.keep_whole or self.counter.count(group.text) <= self._semantic.max_tokens:
                chunks.append(
                    self._chunk(group.text, len(chunks), base | extra, group.keep_whole)
                )
            else:
                for text in self._semantic.split_oversized(group):
                    chunks.append(self._chunk(text, len(chunks), base | extra))
        return chunks

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
