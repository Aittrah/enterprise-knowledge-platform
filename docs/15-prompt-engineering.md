# Milestone 15 — Prompt Engineering

**Module:** `backend/app/prompts/` · **Tests:** `backend/tests/test_prompts.py` (14; suite 192)

## Design

All prompts live in one reviewable library (`PROMPTS`) instead of strings scattered through business logic:

| Template | Purpose |
|---|---|
| `rag_answer` | grounded, cited answer from numbered sources + optional graph facts |
| `router` | pick the best domain agent for a query (M16) |
| `conversation_summary` | compress history for long-term memory (M17) |
| `entity_extraction` | the LLM upgrade path for graph extraction (M10) |
| `suggested_questions` | follow-up suggestions for the chat UI |

## Guarantees

- **Validated templates** — `PromptTemplate` derives its variable set from the template text; rendering with missing *or* unknown variables raises `TemplateError` instead of shipping a broken prompt. `escape_braces()` makes arbitrary user text safe to embed.
- **The citation contract** — `format_context(chunks)` renders numbered source blocks (`[1] leave.pdf (section: Handbook > Leave, pages: 4)`) and returns the citation map `{1: chunk}`; `parse_citations` / `verify_citations` close the loop on the answer side — a `[7]` with no source 7 is an invented citation, detected mechanically. This is the mechanism M20's citation-verification guardrail runs on.
- **Honesty over guessing** — `CITATION_RULES` instruct the model that "the provided documents don't cover this" is the correct answer when sources lack it.
- **Graph facts are citable** — `format_graph_context` renders GraphRAG relations with their evidence sentences, so answers can ground claims in *relationships*, not just passages.
- **Tolerant structured output** — `json_output_rules(schema)` in, `extract_json` out; parsing survives markdown fences and surrounding prose, raising only when there is genuinely no JSON.
