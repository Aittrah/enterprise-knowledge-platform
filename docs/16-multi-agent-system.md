# Milestone 16 — Multi-Agent System

**Module:** `backend/app/agents/` · **Tests:** `backend/tests/test_agents.py` (14; suite 206)

## Architecture

```
question ──> AgentRouter (keyword baseline, optional LLM router with fallback)
                 │
             AgentProfile (persona charter + optional retrieval scope)
                 │
             Agent.answer: retrieve -> format numbered context (+ graph facts)
                           -> rag_answer prompt -> LLM -> verify citations
                 │
             AgentAnswer: text · citations · invalid_citations · grounded ·
                          token usage · retrieval latency
```

`AgentOrchestrator.ask(question, agent_id=None)` is the AI layer's single entry point — routes unless the user pinned an agent in the UI.

## The six agents (`roster.py`)

HR · Finance · Research (default) · Developer · Legal · Operations — each an `AgentProfile` with a router-facing description, a persona charter injected into the system prompt (e.g. Finance: "quote exact figures with currency and period"; Legal: "information, not legal advice"), routing keywords, and an optional retrieval filter scope.

## Routing that never fails

Keyword scoring is the always-available baseline. An LLM router (via the `router` template) can be layered on top and **falls back to keywords** whenever it errors or answers with an unknown agent id — routing is never the reason a question fails.

## Grounding is checked, not assumed

Every answer runs through `verify_citations`: `AgentAnswer.grounded` is true only if the model cited at least one real source and invented none. A reply citing `[9]` when only 6 sources exist surfaces `invalid_citations=[9]` — the M20 guardrails and the UI confidence seal build directly on this.

## LLM client

`OpenAICompatibleClient` speaks `/chat/completions` (the lingua franca — OpenAI, Azure, Groq, Together, or local Ollama by changing `base_url`), mock-tested for payload and usage parsing. Tests run on a scripted `FakeLLM`, so the whole agent stack verifies offline; an Anthropic-native adapter slots in behind the same `LLMClient` protocol.
