# Milestone 17 — Memory System

**Module:** `backend/app/memory/` · **Tests:** `backend/tests/test_memory.py` (14; suite 220)

## Four memory types, one service

| Memory | Mechanism |
|---|---|
| **Conversation** | persistent message history per conversation (SQLite), with a token-budgeted `context_window()` that trims *oldest first* — the current exchange always survives, and the single latest message is returned even if it alone exceeds the budget |
| **Long-term** | `summarize_to_long_term()` distills a conversation via the `conversation_summary` prompt (or a verbatim-tail fallback with no LLM) and stores it as a `summary` fact |
| **User** | `remember("user", id, fact)` / `recall(...)` — preferences, role, recurring topics |
| **Project** | same mechanism scoped to a project id |

## Recall

`recall(scope, id, query)` ranks facts by keyword relevance (embedding-based recall slots in later behind the same signature); without a query it returns the most recent. Scopes are fully isolated and validated.

## Prompt integration

`digest(query, user_id, project_id)` produces a prompt-ready block ("About this user: …", "Project context: …") containing only facts relevant to the query — the orchestrator prepends it so agents answer with persistent context without flooding the prompt.

## Storage

Single SQLite file (stdlib), two tables (`messages`, `facts`), timestamps on everything, persistence verified across instances. PostgreSQL replaces it behind the same `MemoryStore` interface at M18.
