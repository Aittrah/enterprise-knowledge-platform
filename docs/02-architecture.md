# Milestone 2 — System Architecture

**Project:** Enterprise Knowledge Intelligence Platform (EKIP)
**Status:** Approved baseline · Phase 1

Diagrams are authored in Mermaid so they render directly on GitHub; editable draw.io copies can be exported from these definitions.

---

## 1. High-Level Architecture

```mermaid
flowchart LR
    subgraph Client
        FE[React Frontend<br/>TypeScript · Tailwind · shadcn/ui]
    end

    subgraph API["FastAPI Backend"]
        GW[REST + WebSocket Gateway]
        AUTH[Auth Service<br/>JWT · RBAC · SSO]
        GUARD[Guardrails<br/>injection · PII · groundedness]
        ORCH[Agent Orchestrator]
    end

    subgraph Pipeline["Async Workers (Celery + Redis)"]
        ING[Ingestion & OCR]
        CLEAN[Cleaning & Dedup]
        CHUNK[Chunking Engine]
        EMB[Embedding Service + Cache]
        KG[Entity & Relation Extraction]
    end

    subgraph Retrieval["Retrieval Layer"]
        HYB[Hybrid Search<br/>BM25 + Dense + RRF]
        RER[Reranker]
        GRAG[GraphRAG]
    end

    subgraph Storage
        PG[(PostgreSQL<br/>+ pgvector)]
        QD[(Qdrant)]
        NEO[(Neo4j)]
        RED[(Redis)]
        OBJ[(Object Storage<br/>MinIO / S3)]
    end

    subgraph External["LLM / Embedding Providers"]
        LLM[OpenAI · Anthropic · Cohere · Voyage · BGE/E5 local]
    end

    FE <--> GW
    GW --> AUTH
    GW --> GUARD --> ORCH
    ORCH --> HYB --> RER --> ORCH
    ORCH --> GRAG
    ORCH <--> LLM
    GW --> ING
    ING --> CLEAN --> CHUNK --> EMB
    CHUNK --> KG
    EMB --> QD & PG
    KG --> NEO
    ING --> OBJ
    HYB --> QD & PG
    GRAG --> NEO & QD
    EMB <--> RED
    ORCH <--> RED
```

## 2. Low-Level Architecture (backend modules)

```
backend/app/
├── api/                # FastAPI routers: auth, documents, chat, search, graph, analytics, admin
├── core/               # config, security, logging, exceptions, rate limiting
├── ingestion/          # extractors (pdf, docx, txt, html, csv, pptx), ocr/, metadata, versioning
├── processing/         # cleaning, dedup, normalization, chunking strategies
├── embeddings/         # provider adapters (openai, bge, e5, voyage, cohere), cache
├── stores/             # qdrant_store, pgvector_store, neo4j_store, object_store
├── retrieval/          # dense, bm25, hybrid_rrf, reranker, graphrag
├── agents/             # base agent, router, hr, finance, research, developer, legal, operations
├── memory/             # conversation, long_term, user, project memory
├── prompts/            # prompt templates, citation formats, structured output schemas
├── guardrails/         # injection, jailbreak, pii, citation_verify, groundedness
├── evaluation/         # metrics, golden datasets, runners
├── observability/      # structured logs, metrics, tracing, token/cost tracking
├── workers/            # celery tasks: ingest, embed, graph_build, evaluate
└── models/             # SQLAlchemy models + Pydantic schemas
```

Key design decisions (ADR summaries):

| # | Decision | Rationale |
|---|---|---|
| ADR-1 | **FastAPI + Celery** over a single sync app | OCR/embedding are long-running; request path stays fast |
| ADR-2 | **Qdrant primary, pgvector secondary** | Qdrant for scale/filtering; pgvector keeps a SQL-joinable copy for analytics and as fallback |
| ADR-3 | **Provider adapter pattern** for LLM/embeddings | Swap providers per-tenant/per-cost without touching callers |
| ADR-4 | **RRF for hybrid fusion** | No score calibration needed between BM25 and cosine spaces |
| ADR-5 | **Citations = chunk IDs, verified server-side** | Guardrail can prove every citation resolves to retrieved content |
| ADR-6 | **tenant_id everywhere + namespaced collections** | Multi-tenant isolation without separate deployments |

## 3. Data Flow — Ingestion

```mermaid
flowchart TD
    U[Upload] --> S3[Object Storage]
    S3 --> T{Scanned?}
    T -- yes --> OCR[OCR + layout + tables]
    T -- no --> EXT[Native extractor]
    OCR --> META[Metadata generator]
    EXT --> META
    META --> CL[Clean · dedup · normalize]
    CL --> CH[Chunking engine]
    CH --> EMB[Embed + cache]
    CH --> NER[Entity/relation extraction]
    EMB --> VDB[(Qdrant + pgvector)]
    NER --> G[(Neo4j)]
    VDB --> DONE[Status: indexed]
    G --> DONE
```

## 4. Sequence Diagram — Cited chat query

```mermaid
sequenceDiagram
    participant U as User (React)
    participant WS as WebSocket Gateway
    participant G as Guardrails
    participant O as Orchestrator
    participant R as Hybrid Retriever
    participant RR as Reranker
    participant L as LLM Provider

    U->>WS: query + agent selection
    WS->>G: screen input (injection, PII)
    G->>O: safe query
    O->>R: retrieve (BM25 + dense + filters, RRF)
    R->>RR: top-50 candidates
    RR-->>O: top-8 reranked chunks
    O->>L: prompt(context + citations template)
    L-->>O: token stream
    O->>G: verify citations + groundedness
    G-->>WS: stream tokens + citation events
    WS-->>U: streamed answer, citation panel, confidence
    O->>O: persist conversation memory, tokens, cost
```

## 5. Component Diagram — Frontend

```
frontend/src/
├── app/            # router, providers (React Query, Zustand, theme)
├── components/ui/  # shadcn/ui primitives + design-system components
├── components/     # Sidebar, TopNav, ChatWindow, MessageBubble, DocumentCard,
│                   # SearchBar, StatCard, DataTable, Modal, Toast, Timeline,
│                   # GraphViewer, Charts, FileUploadZone, Breadcrumbs
├── features/       # auth, dashboard, chat, knowledge-base, graph, analytics, admin, settings
├── lib/            # api client, ws client, utils
└── stores/         # zustand slices: session, chat, ui
```

## 6. Deployment Diagram

```mermaid
flowchart TB
    subgraph Cloud["Cloud (AWS / Azure / GCP)"]
        LB[Load Balancer / TLS]
        subgraph Containers
            FE2[Frontend - nginx]
            BE[Backend x N - FastAPI]
            WK[Workers x N - Celery]
        end
        subgraph Managed/State
            PG2[(PostgreSQL)]
            QD2[(Qdrant)]
            NEO2[(Neo4j)]
            RED2[(Redis)]
            S32[(S3 / Blob)]
        end
        MON[Prometheus + Grafana + OTel Collector]
    end
    DEV[GitHub Actions CI/CD] -->|build, test, push, deploy| Containers
    LB --> FE2 & BE
    BE & WK --> PG2 & QD2 & NEO2 & RED2 & S32
    BE & WK --> MON
```

Local development mirrors this via `docker-compose.yml` (all stores + API + frontend).

---

*Next milestone: [03-repository-setup](../README.md)*
