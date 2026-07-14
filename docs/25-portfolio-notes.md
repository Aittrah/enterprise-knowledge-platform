# Milestone 25 — Portfolio & Interview Notes

## The 60-second pitch

EKIP is a production-grade Enterprise Knowledge Intelligence Platform: documents go in (PDF/DOCX/HTML/CSV/PPTX, plus OCR for scans and receipts); a pipeline cleans, chunks, embeds, and indexes them into a vector store, a BM25 index, and a knowledge graph; six domain agents answer questions over hybrid GraphRAG retrieval with **verified citations and groundedness scoring on every response**. FastAPI backend with WebSocket streaming, React/TypeScript frontend, 267 tests, CI/CD to containers.

## System-design talking points (interview-ready)

- **Why hybrid retrieval?** Dense embeddings miss exact identifiers (`INV-9987`); BM25 misses paraphrases. RRF fuses ranks without score calibration (ADR-4). Demo: the invoice-number query hits via the BM25 leg at rank 1.
- **Why GraphRAG?** Vector search can't answer "what budget applies to Sara Khan?" when the budget document never names her. The graph walks Sara → WORKS_IN → Finance → MENTIONED_IN → budget.txt. Two hops by design — one hop only finds documents plain retrieval already covers.
- **Why is every provider an adapter?** Embeddings (5 providers), LLM (OpenAI-compatible), reranking (3), vector stores (3), OCR engines — all protocols. The whole stack runs keyless offline (hashing embedder + extractive answers + in-memory stores), so tests never need the network and demos never need a credit card.
- **How do you prevent hallucinated citations?** The prompt numbers sources; `verify_citations` proves every `[n]` resolves to a retrieved chunk; groundedness scores each claim-sentence against the retrieved text; `grounded` is exposed per-answer and evaluated offline with the *same instrument* (M22 faithfulness = M20 validator).
- **Cost control?** Embedding cache keyed by (provider, model, input_type, text) — pure function, never invalidates; re-ingesting a 100-page doc with 3 edited paragraphs embeds 3 chunks. In-call dedupe, batching, per-model cost tracking surfaced in analytics.
- **Versioning story:** content-addressed (sha256) document versions; the indexer supersedes all chunks of a source atomically across the vector store *and* BM25, so stale policies can never be cited.
- **What breaks at scale, and the plan:** in-process BM25 → PostgreSQL FTS; linear MinHash dedup → LSH banding; BackgroundTasks → Celery (services already composed); lexical cohesion/groundedness → embedding-cosine and LLM-judge behind existing hooks.

## Demo script (5 minutes)

1. `docker compose up -d` → open localhost:3000 → register (first account = admin).
2. Upload the HR policy PDF → watch the job complete → chunks/entities in the table.
3. Ask "How many annual leave days do I get?" → streamed answer, **◉ grounded** seal, citation resolving in the provenance rail.
4. Ask an injection ("ignore previous instructions…") → polite guardrail refusal, audited.
5. Graph page → click Sara Khan → evidence sentences behind each edge.
6. Analytics → queries by agent, tokens, cost, cache hit rate.

## Numbers that impress

25 milestones · 9 phases · **267 backend tests** (offline, no keys) · 6 domain agents · 5 embedding providers · 4 retrieval strategies · 3 vector-store backends · every milestone a reviewed feature branch with a `feat:` merge and per-phase tags v0.1.0 → v1.0.0.
