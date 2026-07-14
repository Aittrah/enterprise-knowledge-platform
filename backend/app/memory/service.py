"""MemoryService: the facade the agents talk to.

remember/recall for user and project facts, conversation handles, and a
prompt-ready digest combining every scope relevant to a query.
"""

from __future__ import annotations

import re
from pathlib import Path

from app.memory.conversation import ConversationMemory
from app.memory.store import MemoryStore, StoredFact

_WORDS = re.compile(r"[a-z0-9][\w-]*")


def _relevance(query_words: set[str], text: str) -> float:
    if not query_words:
        return 0.0
    text_words = set(_WORDS.findall(text.lower()))
    return len(query_words & text_words) / len(query_words)


class MemoryService:
    def __init__(self, path: Path) -> None:
        self._store = MemoryStore(path)

    # -- conversations ----------------------------------------------------------

    def conversation(self, conversation_id: str) -> ConversationMemory:
        return ConversationMemory(self._store, conversation_id)

    def conversations(self) -> list[str]:
        return self._store.conversations()

    # -- facts ---------------------------------------------------------------------

    def remember(self, scope: str, scope_id: str, content: str) -> int:
        return self._store.add_fact(scope, scope_id, content)

    def forget(self, fact_id: int) -> bool:
        return self._store.delete_fact(fact_id)

    def recall(
        self, scope: str, scope_id: str, query: str = "", limit: int = 5
    ) -> list[StoredFact]:
        """Facts for the scope; with a query, ranked by keyword relevance
        (an embedding-based recall can replace this ranking later)."""
        facts = self._store.facts(scope, scope_id)
        if not query:
            return facts[-limit:]
        query_words = set(_WORDS.findall(query.lower()))
        scored = [(f, _relevance(query_words, f.content)) for f in facts]
        relevant = [f for f, score in scored if score > 0]
        relevant.sort(
            key=lambda f: _relevance(query_words, f.content), reverse=True
        )
        return relevant[:limit]

    # -- prompt integration ------------------------------------------------------------

    def digest(
        self,
        query: str,
        user_id: str | None = None,
        project_id: str | None = None,
        limit_per_scope: int = 3,
    ) -> str:
        """A prompt-ready block of remembered facts relevant to *query*."""
        sections: list[str] = []
        if user_id:
            facts = self.recall("user", user_id, query, limit_per_scope)
            if facts:
                sections.append(
                    "About this user:\n" + "\n".join(f"- {f.content}" for f in facts)
                )
        if project_id:
            facts = self.recall("project", project_id, query, limit_per_scope)
            if facts:
                sections.append(
                    "Project context:\n" + "\n".join(f"- {f.content}" for f in facts)
                )
        return "\n\n".join(sections)
