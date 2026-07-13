"""KnowledgeBaseIndexer — the write path of the knowledge base.

document -> chunks (M7) -> vectors (M8) -> vector store (M9), superseding
any previously indexed version of the same source so stale chunks can
never surface in retrieval.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.embeddings.service import EmbeddingService
from app.ingestion.models import DocumentMetadata, ExtractedDocument
from app.processing.chunking import ChunkGenerator, ChunkValidator, ValidationReport
from app.stores.base import StoreError, VectorRecord, VectorStore


@dataclass
class IndexReport:
    source: str
    chunks_indexed: int
    superseded_previous: bool
    validation: ValidationReport


class KnowledgeBaseIndexer:
    def __init__(
        self,
        store: VectorStore,
        embeddings: EmbeddingService,
        generator: ChunkGenerator | None = None,
        validator: ChunkValidator | None = None,
    ) -> None:
        self._store = store
        self._embeddings = embeddings
        self._generator = generator or ChunkGenerator()
        self._validator = validator or ChunkValidator()

    def index(
        self, document: ExtractedDocument, metadata: DocumentMetadata
    ) -> IndexReport:
        chunks = self._generator.generate(document, metadata)
        report = self._validator.validate(chunks, document)
        if not report.ok:
            raise StoreError(
                f"refusing to index {metadata.filename}: " + "; ".join(report.issues)
            )

        vectors = self._embeddings.embed_texts([c.text for c in chunks])
        self._store.ensure_ready(self._embeddings.provider.dimension)

        # Supersede: a new version replaces every chunk of the old one.
        superseded = self._store.count() > 0 and bool(
            self._store.search(vectors[0], top_k=1, filters={"source": metadata.filename})
        )
        self._store.delete_by_filter({"source": metadata.filename})

        self._store.upsert(
            [
                VectorRecord(id=c.id, vector=v, text=c.text, metadata=c.metadata)
                for c, v in zip(chunks, vectors)
            ]
        )
        return IndexReport(
            source=metadata.filename,
            chunks_indexed=len(chunks),
            superseded_previous=superseded,
            validation=report,
        )
