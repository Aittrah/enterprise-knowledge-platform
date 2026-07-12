# Milestone 1 — Requirements Specification

**Project:** Enterprise Knowledge Intelligence Platform (EKIP)
**Status:** Approved baseline · Phase 1
**Author:** Aittrah Sardar

---

## 1. Project Scope

EKIP is a production-grade platform that lets organizations ingest their internal documents (policies, contracts, reports, invoices, wikis), build a searchable knowledge base with vector + graph representations, and query it through specialized AI agents with verifiable citations.

**In scope**

- Multi-format document ingestion (PDF, DOCX, TXT, HTML, CSV, PPTX) with OCR for scanned material
- Hybrid retrieval: dense vectors, BM25, metadata filters, reciprocal rank fusion, reranking, GraphRAG
- Multi-agent AI layer (HR, Finance, Research, Developer, Legal, Operations) with conversation and long-term memory
- FastAPI backend (REST + WebSocket streaming), React/TypeScript frontend
- AI guardrails: prompt-injection detection, PII detection, citation verification, groundedness validation
- Evaluation framework (faithfulness, precision/recall, hallucination rate, latency, cost) and observability
- CI/CD with Docker; cloud deployment

**Out of scope (v1)**

- Model fine-tuning / training
- Real-time collaborative editing of documents
- On-premise air-gapped installer
- Mobile native apps (responsive web only)

## 2. User Personas

| Persona | Description | Primary needs |
|---|---|---|
| **Knowledge Worker** (analyst, HR staff, engineer) | Asks questions against company documents daily | Fast, cited, trustworthy answers; chat history; file upload |
| **Department Lead** | Reviews team usage and answer quality | Analytics, feedback trends, agent performance |
| **Platform Admin** | Operates the system | User/role management, model & provider configuration, API keys, monitoring |
| **Compliance Officer** | Audits AI output | Citations, groundedness scores, PII handling, audit logs |
| **AI Engineer (maintainer)** | Extends the platform | Clean architecture, evaluation dashboard, tracing |

## 3. Functional Requirements

**FR-1 Ingestion**
- FR-1.1 Upload PDF, DOCX, TXT, HTML, CSV, PPTX up to 100 MB per file
- FR-1.2 OCR scanned PDFs, images, receipts, invoices (layout + table detection)
- FR-1.3 Extract and store metadata (title, author, date, department, tags, version)
- FR-1.4 Track document versions; re-ingestion supersedes prior chunks

**FR-2 Knowledge Base**
- FR-2.1 Clean, deduplicate, and normalize extracted text
- FR-2.2 Chunk with semantic / recursive / token-based strategies (configurable)
- FR-2.3 Embed with pluggable providers (OpenAI, BGE, E5, Voyage, Cohere) + cache
- FR-2.4 Store vectors in Qdrant and PostgreSQL/pgvector; entities & relations in Neo4j

**FR-3 Retrieval**
- FR-3.1 Dense semantic search with similarity threshold
- FR-3.2 Hybrid search: BM25 + vectors + metadata filters fused via RRF
- FR-3.3 Rerank with cross-encoder or Cohere Rerank
- FR-3.4 GraphRAG: combine graph traversal with vector retrieval

**FR-4 AI Layer**
- FR-4.1 Six domain agents (HR, Finance, Research, Developer, Legal, Operations) with routing
- FR-4.2 Streaming answers with inline citations to source chunks
- FR-4.3 Conversation, user, and project memory
- FR-4.4 Structured output support (JSON mode) for downstream automation

**FR-5 Application**
- FR-5.1 Authentication (email/password + Google/Microsoft SSO), JWT sessions, RBAC (user / admin)
- FR-5.2 Screens: Login/Register, Dashboard, AI Chat, Knowledge Base, Knowledge Graph, Analytics, Admin, Settings
- FR-5.3 WebSocket streaming chat with markdown, code highlighting, copy/export
- FR-5.4 Admin: users, roles, documents, providers, API keys, monitoring, feedback

**FR-6 Trust & Safety**
- FR-6.1 Detect prompt injection and jailbreak attempts before LLM calls
- FR-6.2 Detect and mask PII in ingested content and answers
- FR-6.3 Verify every citation points at a real retrieved chunk
- FR-6.4 Score answer groundedness; flag low-confidence responses in UI

**FR-7 Evaluation & Observability**
- FR-7.1 Offline eval suite: context precision/recall, faithfulness, hallucination rate
- FR-7.2 Runtime metrics: latency, token usage, cost per query/user/agent
- FR-7.3 Structured logging + tracing across the RAG pipeline

## 4. Non-Functional Requirements

| Category | Requirement |
|---|---|
| Performance | First streamed token < 2 s (p50); retrieval < 500 ms (p95); ingestion 10 pages/s excluding OCR |
| Scalability | Stateless API horizontally scalable; async workers for ingestion; 1 M+ chunks per tenant |
| Availability | 99.5 % target; graceful degradation if a provider is down (fallback provider) |
| Security | TLS everywhere, hashed passwords (bcrypt), scoped API keys, rate limiting, audit logs |
| Privacy | PII masking, per-role document access, no training on customer data |
| Usability | WCAG 2.1 AA, keyboard navigable, dark + light mode, responsive ≥ 360 px |
| Maintainability | Typed code (mypy / TypeScript strict), > 80 % unit coverage on core pipeline, docs per module |
| Cost | Token & embedding cache; cost dashboard; configurable cheaper-model routing |

## 5. System Constraints

- LLM and embedding providers are external paid APIs — all calls must be cached, budgeted, and traceable
- OCR is CPU/GPU intensive — must run in background workers, never in request path
- Neo4j, Qdrant, PostgreSQL, Redis run as containers; local dev must work with Docker Compose only
- Single-region deployment in v1; multi-tenant isolation by tenant_id column + collection namespacing

## 6. Assumptions

- Documents are in English (multilingual is a later milestone)
- Users belong to one organization; cross-org sharing is out of scope
- An OpenAI-compatible API key is available for development; local models optional via BGE/E5
- Interviewer/demo audience: the platform doubles as a portfolio flagship, so every module ships with docs and tests

## 7. Use Cases

**UC-1 Ask a cited question** — Knowledge Worker selects the HR Agent, asks "How many annual leave days do I have?", receives a streamed answer with citations into the leave policy PDF, opens the cited page in the preview panel.

**UC-2 Ingest a contract** — Admin uploads a scanned contract PDF; OCR extracts text and tables; pipeline cleans, chunks, embeds, and indexes it; entities (parties, dates, amounts) land in the knowledge graph; status is visible in the Knowledge Base screen.

**UC-3 Audit an answer** — Compliance Officer opens a flagged conversation, inspects groundedness score, citations, and the exact retrieved chunks; exports the audit trail.

**UC-4 Tune retrieval** — AI Engineer runs the evaluation suite against a golden dataset, compares hybrid vs. dense-only retrieval in the Evaluation Dashboard, and promotes the better configuration.

**UC-5 Control spend** — Admin sets a monthly token budget per department, watches cost analytics, and routes low-stakes queries to a cheaper model.

## 8. Feature List (condensed)

Ingestion pipeline · OCR module · Cleaning & dedup · Chunking engine · Embedding service + cache · Qdrant + pgvector storage · Knowledge graph (Neo4j) · Semantic / hybrid / reranked / GraphRAG retrieval · Prompt library · Multi-agent framework · Memory service · FastAPI backend (REST + WS) · React frontend (8 screens) · Guardrails · Evaluation framework · Monitoring · CI/CD · Cloud deployment · Documentation

---

*Next milestone: [02-architecture.md](02-architecture.md)*
