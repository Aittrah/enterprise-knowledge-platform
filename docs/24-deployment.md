# Milestones 24–25 — CI/CD & Cloud Deployment

## CI/CD (`.github/workflows/ci.yml`)

Every push and PR: backend lint (ruff) + 267 tests with pip cache and Tesseract installed; frontend strict typecheck + production build with npm cache. Pushes to `main` additionally build both Docker images with BuildKit layer caching and publish to **GHCR** (`ekip-backend`, `ekip-frontend`) tagged by branch, semver tag, and commit SHA. Version tags (`v*`) trigger the gated `production` deploy job — wire it to your target below.

## Containers

- `backend/Dockerfile` — python:3.12-slim + Tesseract, non-root user, uvicorn on :8000
- `frontend/Dockerfile` — node build stage → nginx serving the SPA and proxying `/api` (incl. WebSocket upgrade) to the `backend` service
- `docker-compose.yml` — the full stack: `docker compose up -d` gives you Postgres+pgvector, Qdrant, Neo4j, Redis, MinIO, the API (wired to Qdrant), and the web UI on **http://localhost:3000**

## Production environment variables

| Variable | Production value |
|---|---|
| `JWT_SECRET` | long random string (secrets manager) |
| `VECTOR_STORE` / `QDRANT_URL` | `qdrant` / managed or self-hosted Qdrant URL |
| `EMBEDDING_PROVIDER` + key | `openai` (or `cohere`/`voyage`) |
| `OPENAI_API_KEY`, `LLM_MODEL` | enables synthesized answers |
| `CORS_ORIGINS` | your frontend origin |
| `EKIP_DATA_DIR` | mounted volume |

## Cloud targets (one image pair, three options)

**AWS** — App Runner (simplest: point both services at the GHCR images, set env vars, done) or ECS Fargate behind an ALB for scale. Managed stores: Aurora PostgreSQL + pgvector, Qdrant Cloud, Neptune or self-hosted Neo4j on ECS, ElastiCache, S3 (replace MinIO envs).

**Azure** — Container Apps (two apps + ingress), Azure Database for PostgreSQL, Qdrant on Container Apps or Qdrant Cloud, Blob Storage.

**GCP** — Cloud Run (two services; set `--allow-unauthenticated` on frontend only), Cloud SQL Postgres, Qdrant Cloud, GCS.

Steps are identical everywhere: (1) create the managed stores, (2) put secrets in the platform's secret manager, (3) deploy the two images with the env table above, (4) point the frontend's `/api` proxy (nginx env or platform ingress rule) at the backend service, (5) run the golden-dataset evaluation (M22) against the deployed API as a smoke gate.

## Scaling notes

The API is stateless (JWT auth, external stores) — scale horizontally. Ingestion currently runs in-process via BackgroundTasks; at volume, move `AppState.run_ingestion` onto Celery + Redis (compose services already present, same function signature). The in-memory BM25 index rebuilds from the vector store on boot; swap for PostgreSQL FTS when corpus size demands.
