# Milestone 8 — Embedding Pipeline

**Module:** `backend/app/embeddings/` · **Tests:** `backend/tests/test_embeddings.py` (20; suite 95)

## What it does

The single path through which the platform turns text into vectors:

```python
from app.embeddings import EmbeddingService, create_provider

service = EmbeddingService(create_provider("openai"), cache_path=Path("data/embeddings.db"))
vectors = service.embed_texts([chunk.text for chunk in chunks])   # documents
query_vector = service.embed_query("how many leave days do I get?")  # queries
```

## Providers

| Name | Backend | Notes |
|---|---|---|
| `openai` | REST, `text-embedding-3-small`/`-large` | symmetric — same embedding for query & doc |
| `cohere` | REST, embed v2 | maps to `search_query` / `search_document` |
| `voyage` | REST, `voyage-3` family | native `input_type` parameter |
| `bge`, `e5` | local via sentence-transformers (optional install) | prefix conventions applied to the text itself |
| `hashing` | pure Python feature hashing | keyless/offline dev fallback — see below |

Adapters speak plain REST via httpx (one dependency, uniform errors, `MockTransport`-testable) instead of five vendor SDKs. All are `EmbeddingProvider` protocol: `embed(texts, input_type) -> vectors`.

**`input_type` is part of the contract** because retrieval-tuned models embed queries and documents differently — E5 needs `query:`/`passage:` prefixes, BGE prefixes queries only, Cohere/Voyage take a parameter. Callers just say which side they're on; adapters translate.

**The `hashing` provider** hashes word uni/bigrams into a signed, L2-normalized 384-dim vector. It has no semantics, but lexically similar texts land close — enough to develop and demo the entire retrieval stack (M9–M14) offline at zero cost. Never the production embedder.

## Cache

SQLite (stdlib), float32 blobs, keyed by `blake2b(provider:model:input_type:text)` — embeddings are pure functions of that tuple, so entries never invalidate. Re-ingesting a 100-page document with three edited paragraphs re-embeds three chunks. Query and document embeddings cache separately by design.

## Service guarantees

- **Cache-first:** only misses reach the provider (`stats` tracks hits/misses/batches)
- **Deduplicated:** identical texts within one call are embedded once
- **Batched:** provider calls capped at `batch_size` (default 64)
- **Retrying:** transient `ProviderRequestError`s retried with exponential backoff; configuration errors (missing key) fail immediately with the env var named
- **Shape-checked:** a provider returning the wrong number of vectors raises instead of silently misaligning chunks and embeddings
