"""Vector + metadata storage.

One ``VectorStore`` protocol, three backends:

    memory   — exact search, zero dependencies; unit tests and offline dev
    qdrant   — primary production store (REST via httpx)
    pgvector — SQL-joinable secondary store (PostgreSQL + pgvector)

``KnowledgeBaseIndexer`` is the write path: document -> chunks -> vectors
-> upsert, superseding prior versions of the same source.
"""

from app.stores.base import SearchHit, StoreError, VectorRecord, VectorStore
from app.stores.indexer import IndexReport, KnowledgeBaseIndexer
from app.stores.memory import InMemoryVectorStore
from app.stores.qdrant import QdrantVectorStore

__all__ = [
    "IndexReport",
    "InMemoryVectorStore",
    "KnowledgeBaseIndexer",
    "QdrantVectorStore",
    "SearchHit",
    "StoreError",
    "VectorRecord",
    "VectorStore",
]
