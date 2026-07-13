"""The prompt library: every named template the platform uses.

Templates live in one place so prompt changes are reviewable diffs, not
string edits scattered through business logic.
"""

from __future__ import annotations

from app.prompts.citations import CITATION_RULES
from app.prompts.templates import PromptTemplate

PROMPTS: dict[str, PromptTemplate] = {}


def _register(template: PromptTemplate) -> None:
    PROMPTS[template.name] = template


_register(
    PromptTemplate(
        name="rag_answer",
        description="Grounded, cited answer from retrieved context",
        system=(
            "You are {agent_name}, an enterprise knowledge assistant. "
            "{agent_charter} "
            "Answer strictly from the numbered sources provided. "
            + CITATION_RULES
            + " Keep answers concise and structured; use markdown where it helps."
        ),
        user=(
            "Sources:\n\n{context}\n\n{graph_context}\n\n"
            "Question: {question}\n\n"
            "Answer with citations:"
        ),
    )
)

_register(
    PromptTemplate(
        name="router",
        description="Pick the best domain agent for a query",
        system=(
            "You route enterprise questions to the single best-suited agent. "
            "Available agents:\n{agents}\n"
            "Respond with only the agent id, nothing else."
        ),
        user="Question: {question}\n\nBest agent id:",
    )
)

_register(
    PromptTemplate(
        name="conversation_summary",
        description="Compress a conversation for long-term memory",
        system=(
            "Summarize the conversation for future recall. Capture decisions, "
            "facts about the user, and open questions in at most {max_words} words. "
            "Write plain declarative sentences."
        ),
        user="Conversation:\n{conversation}\n\nSummary:",
    )
)

_register(
    PromptTemplate(
        name="entity_extraction",
        description="LLM upgrade path for graph entity extraction (M10)",
        system=(
            "Extract entities and relationships from enterprise text. "
            "{format_rules}"
        ),
        user="Text:\n{text}\n\nJSON:",
    )
)

_register(
    PromptTemplate(
        name="suggested_questions",
        description="Follow-up question suggestions after an answer",
        system=(
            "Given a question and its answer, propose {count} short natural "
            "follow-up questions the user is likely to ask next. "
            "Return them as a JSON array of strings, nothing else."
        ),
        user="Question: {question}\nAnswer: {answer}\n\nJSON array:",
    )
)
