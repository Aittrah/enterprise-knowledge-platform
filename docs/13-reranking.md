# Milestone 13 — Reranking

**Module:** `backend/app/retrieval/rerank.py` · **Tests:** `backend/tests/test_rerank.py` (14; suite 171)

## Why rerank

First-stage retrieval (dense/hybrid) optimizes *recall* over the whole corpus using representations computed before the query existed. A reranker reads the query against each surviving candidate together and re-scores with far more precision. Standard two-stage pattern: retrieve wide, rerank narrow.

```python
retriever = RerankedRetriever(
    HybridRetriever(store, embeddings, bm25),
    CohereReranker(),          # or CrossEncoderReranker() / LexicalReranker()
    candidate_k=30,
)
result = retriever.retrieve("how many leave days?", top_k=8)
```

## Backends (one `Reranker` protocol)

| Backend | How | When |
|---|---|---|
| `CohereReranker` | Rerank v2 REST (httpx, MockTransport-tested) | production, no GPU |
| `CrossEncoderReranker` | local ms-marco cross-encoder (optional sentence-transformers install) | production, self-hosted |
| `LexicalReranker` | content-word overlap + phrase-adjacency bonus, normalized to [0,1] | offline dev/demo — deterministic and free |

## RerankedRetriever

Composes any `Retriever` with any `Reranker` while preserving the Retriever contract — the AI layer can't tell whether reranking is on:

- names itself `"{first_stage}+{reranker}"` (e.g. `hybrid+cohere-rerank`)
- first-stage scores survive as `metadata["retrieval_score"]`; `chunk.score` becomes the rerank relevance — evaluation (M22) can compare the stages
- `debug` carries both stages: first-stage internals, timings, candidates reranked

## Note from development

The lexical reranker originally clamped scores at 1.0, which silently erased the phrase bonus whenever term overlap was already perfect — caught by the bigram test, fixed by normalizing `(overlap + bonus) / 1.5` instead of clamping.
