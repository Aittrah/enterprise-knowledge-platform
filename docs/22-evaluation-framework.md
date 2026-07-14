# Milestone 22 — Evaluation Framework

**Module:** `backend/app/evaluation/` · **Tests:** `backend/tests/test_evaluation.py` (7)

## What it measures

```python
dataset = GoldenDataset.load(Path("eval/golden.json"))   # reviewable JSON cases
runner = EvaluationRunner(retriever, orchestrator)

runner.evaluate_retrieval(dataset, k=5).aggregates
# context_precision · context_recall · mrr · hit_rate · latency_p50/p95_ms

runner.evaluate_answers(dataset).aggregates
# faithfulness · hallucination_rate · citation_accuracy · keyword_coverage · grounded_share
```

Every roadmap metric is covered: precision, recall, faithfulness, hallucination rate, context precision/recall, latency, and cost (cost lives in M23's tracker, aggregated per query).

## Design decisions

- **A golden case is data, not code** — `{question, relevant_sources, expected_keywords, agent_id}` in JSON, so domain experts can add cases via PR review.
- **Faithfulness reuses the M20 groundedness validator** — evaluation and runtime guardrails measure hallucination with the same instrument; hallucination rate is defined as its complement, so offline scores predict online behavior.
- **Citation accuracy** = valid citations ÷ citations made; an answer that cites `[9]` out of 6 sources scores below 1.0 mechanically.
- Per-case rows ride along in every report for drill-down; `to_dict()` feeds the Evaluation Dashboard (Module 21) and CI regression checks (compare aggregates between runs).

# Milestone 23 — Monitoring & Observability

**Module:** `backend/app/observability/` · **Tests:** `backend/tests/test_observability.py` (9; suite 267)

| Piece | What it does |
|---|---|
| **Structured logging** | JSON lines (`ts`, `level`, `logger`, `message` + arbitrary fields via `log_event`) — machine-parseable from day one; configured at app startup |
| **MetricsRegistry** | thread-safe counters + latency observations (ring-buffered), JSON snapshot and **Prometheus text exposition** — Prometheus scrapes `/api/monitoring/prometheus`, Grafana graphs it |
| **Request middleware** | every HTTP request recorded: `ekip_http_requests_total{method,path,status}` + latency histogram per path |
| **Query metrics** | `ekip_queries_total{agent}`, `ekip_retrieval_ms`, `ekip_tokens_total` recorded in the ask path |
| **Cost tracking** | per-model USD pricing table; every chat adds to `cost_usd` in analytics; unknown models are estimated *and marked* |
| **Tracer** | nested span context managers for the RAG pipeline (`ask` → `retrieve` → `llm`); span names are the contract OpenTelemetry adopts at deployment |

Endpoints: `GET /api/monitoring/metrics` (JSON) · `GET /api/monitoring/prometheus` (text) — both JWT-gated.
