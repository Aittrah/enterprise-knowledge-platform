# Milestone 12 — Hybrid Search

**Module:** `backend/app/retrieval/` (bm25, fusion, hybrid) · **Tests:** `backend/tests/test_retrieval_hybrid.py` (16; suite 157)

## Why hybrid

Dense retrieval misses exactly what enterprises search for most: invoice numbers, employee names, error codes, acronyms. BM25 nails those but misses paraphrases. The hybrid engine runs both and fuses ranks:

```python
bm25 = BM25Index()
indexer = KnowledgeBaseIndexer(store, embeddings, text_index=bm25)  # keeps both in sync
retriever = HybridRetriever(store, embeddings, bm25)
result = retriever.retrieve("INV-9987 reimbursement", filters={"file_type": "pdf"})
```

## Components

- **`BM25Index`** — Okapi BM25 (k1 = 1.5, b = 0.75), pure Python, ingests the same `VectorRecord`s as the vector store. Tokenizer keeps hyphenated identifiers (`inv-9987`) whole. In-memory for this milestone; swaps for PostgreSQL FTS at scale.
- **`reciprocal_rank_fusion`** — per ADR-4, fuses rankings from incomparable score spaces using ranks only: `Σ weight / (k + rank)`, k = 60. Documents that both retrievers agree on rise to the top. Each fused item records the rank it got from every leg.
- **`HybridRetriever`** — pulls 50 candidates per leg (filters applied to both), fuses, normalizes scores so the top hit is 1.0 (stable scale for the confidence UI and the M13 reranker), and reports `dense_candidates` / `bm25_candidates` / `overlap` in `debug`. Every returned chunk carries its `fusion_ranks` — you can always see *why* it ranked.

## Index synchronization

`KnowledgeBaseIndexer` mirrors every upsert/supersede into the BM25 index, so re-ingesting a document atomically replaces it on both legs — verified by a test that re-ingests an invoice and confirms the old invoice number is unreachable by keyword while the new one hits.

## Verified behavior

- `INV-9987` → the invoice document, rank 1 from BM25 (dense alone can't guarantee this)
- "how many annual leave days do employees receive" → the leave policy (semantic leg)
- Rare terms outweigh common ones (IDF), weights can bias either leg, filters scope both
