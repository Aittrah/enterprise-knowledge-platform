# Milestone 11 — Semantic Search

**Module:** `backend/app/retrieval/` · **Tests:** `backend/tests/test_retrieval_dense.py` (10; suite 141)

## The Retriever API

Every retrieval strategy (dense here; hybrid M12, reranked M13, GraphRAG M14) implements one contract:

```python
result = retriever.retrieve("how many leave days do I get?", top_k=8,
                            filters={"source": "leave-policy.pdf"})
result.chunks        # RetrievedChunk: id, text, score, provenance metadata
result.sources       # unique source documents, in rank order
result.elapsed_ms    # latency (feeds M22 evaluation / M23 monitoring)
result.debug         # candidates, below_threshold, strategy internals
```

`RetrievedChunk` is the unit the AI layer builds prompts and citations from — score and provenance travel together from the store to the final answer.

## DenseRetriever

1. Embed the query with `input_type="query"` — a test pins this, because embedding queries document-side silently degrades E5/BGE/Cohere retrieval.
2. Vector-store similarity search (any `VectorStore` backend, filters pass through).
3. **Similarity threshold** (`min_score`, default 0.25): the first groundedness control in the stack. Chunks below it are noise that would pad the prompt and invite hallucinated citations — fewer honest results beat padded ones. Dropped counts surface in `debug`.

## Similarity search

`retriever.similar(text, exclude_id=...)` returns the chunks most like a given passage (document-side embedding, self excluded) — powering "related passages" in the Knowledge Base preview.

## Verified offline

The test corpus (HR policy, expense policy, Kubernetes notes) runs on the in-memory store + hashing embedder: relevance ranking, threshold behavior, filter scoping, and top-k limits all hold with zero services. Swapping in Qdrant + OpenAI changes construction arguments, not behavior.
