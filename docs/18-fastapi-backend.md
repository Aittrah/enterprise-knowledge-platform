# Milestone 18 — FastAPI Backend

**Module:** `backend/app/api/` + `app/core/` · **Tests:** `backend/tests/test_api.py` (16; suite 236)

## Run it

```bash
cd backend
uvicorn app.api.main:create_app --factory --reload
# OpenAPI docs at http://localhost:8000/api/docs
```

**Keyless defaults**: in-memory vector store + hashing embedder + *extractive* answers — the API works on a fresh clone with zero services. `.env` switches on the real stack (`VECTOR_STORE=qdrant`, `EMBEDDING_PROVIDER=openai`, `OPENAI_API_KEY=...` for synthesized LLM answers).

## Surface

| Endpoint | What |
|---|---|
| `POST /api/auth/register` · `/login` · `GET /me` | JWT auth (PBKDF2 passwords); **first account becomes admin**; `GET /auth/users` is admin-only |
| `POST /api/documents/upload` | multipart upload → **background ingestion job** (extract → OCR fallback → clean → chunk → embed → index → graph); extension + size validated; `GET /documents`, `GET /documents/jobs/{id}` |
| `POST /api/chat` | routed agent answer with citations, groundedness, token usage |
| `WS /api/chat/ws?token=` | **streaming chat**: `start` → `token`* → `done` (citations, grounded, latency); JWT-gated |
| `GET /api/chat/agents` · `/conversations` · `/conversations/{id}` | roster + persistent history (M17 memory) |
| `POST /api/search` | direct GraphRAG retrieval with scores, sources, fusion debug |
| `GET /api/graph/viz` · `/search` · `/neighbors` · `/stats` | GraphViewer data contract (M10) |
| `GET /api/analytics/summary` | documents, chunks, queries by agent, tokens, cache hits, active providers |
| `GET /health` | liveness |

## Design notes

- **`AppState`** (`state.py`) is the single composition root — every service built in Phases 2–5 is wired there once; routers only see dependencies.
- **ExtractiveLLM fallback** — without an API key, answers are assembled from the top retrieved source blocks, properly cited and honestly labeled ("extractive mode"). Demo-able everywhere; a key upgrades quality, not correctness.
- **Background workers** — ingestion runs via `BackgroundTasks` with a job-status API; Celery + Redis replace this transparently when deployment scale demands (compose services already defined).
- **Fixed during testing:** SQLite connections were thread-pinned while FastAPI serves sync endpoints from a threadpool — `check_same_thread=False` on the memory store and embedding cache; caught by the API tests, not in production.
