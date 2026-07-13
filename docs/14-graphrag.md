# Milestone 14 — GraphRAG

**Module:** `backend/app/retrieval/graphrag.py` · **Tests:** `backend/tests/test_graphrag.py` (7; suite 178)

## What it adds over hybrid search

Vector/BM25 search answers "what text sounds like the query". The graph answers "what is **connected** to the things the query names". GraphRAG fuses both:

1. Extract entities from the query and match them to graph nodes (falls back to node-name search for lowercase mentions).
2. Expand the neighborhood — **depth 2 by design**: query entity → shared entity → *that* entity's documents. Depth 1 would only find documents the query entity itself appears in, which plain retrieval already covers.
3. Run a second retrieval scoped to graph-implicated documents with the query enriched by related entity names.
4. RRF-fuse the vector leg and the graph leg (normalized scores, `fusion_ranks` on every chunk).

## The proof case (from the tests)

Corpus: `team.txt` says Sara Khan works in Finance; `budget.txt` states the Finance travel budget **without ever naming Sara**. Query: *"What budget applies to Sara Khan?"*

- Hybrid retrieval alone surfaces only `team.txt` — no lexical or vector overlap ties Sara to the budget document.
- GraphRAG walks Sara → `WORKS_IN` → Finance → `MENTIONED_IN` → `budget.txt` and returns both documents.

## Graph reasoning is inspectable

`debug` carries `matched_entities`, `related_entities`, `graph_documents`, and `graph_context` — the actual relations used, each with its evidence sentence. The AI layer (M15+) can cite *relationships*, not just passages; queries with no graph matches degrade cleanly to the vector leg.
