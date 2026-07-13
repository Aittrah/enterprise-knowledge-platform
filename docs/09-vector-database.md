# Milestone 9 — Vector Database

**Module:** `backend/app/stores/` · **Tests:** `backend/tests/test_stores.py` (19; suite 113 + 1 live-integration)

## What it does

Vector + metadata storage behind one `VectorStore` protocol, and the knowledge-base **write path**:

```python
from app.stores import KnowledgeBaseIndexer, QdrantVectorStore
from app.embeddings import EmbeddingService, create_provider

indexer = KnowledgeBaseIndexer(QdrantVectorStore(), EmbeddingService(create_provider("openai")))
report = indexer.index(result.document, result.metadata)
# report.chunks_indexed, report.superseded_previous, report.validation
```

## Backends

| Store | Role | Notes |
|---|---|---|
| `QdrantVectorStore` | primary (ADR-2) | REST via httpx — same pattern as the embedding adapters, MockTransport-tested, no qdrant-client dependency. Chunk ids (32-hex blake2b) map 1:1 onto Qdrant's required UUID point ids |
| `PgVectorStore` | secondary | SQL-joinable copy for analytics + fallback; JSONB metadata, `vector(dim)` column, cosine ops; psycopg3 is an optional install |
| `InMemoryVectorStore` | reference/dev | exact cosine search; the contract's executable spec. Paired with the `hashing` embedder, the full stack runs offline |

## The filter contract

Retrieval code passes plain dicts — `{"source": "policy.pdf"}` (equality), `{"file_type": ["pdf", "docx"]}` (membership) — and each backend translates: Qdrant `must`/`match` clauses, SQL `metadata->>key` predicates, or Python matching. M12's metadata-filtered hybrid search builds directly on this.

## Indexer guarantees

- **Validation gate:** an invalid chunk set (per M7's `ChunkValidator`) refuses to index — nothing is partially written.
- **Supersedence:** indexing a document deletes every previously stored chunk of the same source first. Combined with M4's version tracking, a stale version can never surface in retrieval.
- **Dimension safety:** the store is initialized from the embedding provider's dimension, so provider switches fail loudly at `ensure_ready`, not silently at query time.

## Integration tests

`test_qdrant_live_roundtrip` runs the full ensure → upsert → search → delete cycle against a real Qdrant and **auto-skips while Docker is down**. Start the stores with `docker compose up -d` and the test joins the suite.
