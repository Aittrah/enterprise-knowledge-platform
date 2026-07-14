"""Conversation memory: persistent history with a token-budgeted window

and summarization into long-term memory.
"""

from __future__ import annotations

from app.agents.llm import LLMClient
from app.memory.store import MemoryStore, StoredMessage
from app.processing.chunking.tokens import DEFAULT_COUNTER, TokenCounter
from app.prompts import PROMPTS
from app.prompts.templates import escape_braces


class ConversationMemory:
    def __init__(
        self,
        store: MemoryStore,
        conversation_id: str,
        counter: TokenCounter = DEFAULT_COUNTER,
    ) -> None:
        self._store = store
        self.conversation_id = conversation_id
        self._counter = counter

    def add(self, role: str, content: str) -> None:
        self._store.add_message(self.conversation_id, role, content)

    def history(self) -> list[StoredMessage]:
        return self._store.messages(self.conversation_id)

    def context_window(self, max_tokens: int = 2000) -> list[dict[str, str]]:
        """Most recent messages that fit the budget, oldest first —
        trimming drops from the *start* so the current exchange survives."""
        window: list[dict[str, str]] = []
        used = 0
        for message in reversed(self.history()):
            cost = self._counter.count(message.content)
            if window and used + cost > max_tokens:
                break
            window.append({"role": message.role, "content": message.content})
            used += cost
        window.reverse()
        return window

    def summarize_to_long_term(
        self, llm: LLMClient | None = None, max_words: int = 120
    ) -> str:
        """Distill the conversation into a summary fact. With no LLM, fall
        back to storing the last exchanges verbatim (still useful recall)."""
        transcript = "\n".join(f"{m.role}: {m.content}" for m in self.history())
        if not transcript:
            return ""
        if llm is not None:
            messages = PROMPTS["conversation_summary"].render(
                conversation=escape_braces(transcript), max_words=max_words
            )
            summary = llm.chat(messages, temperature=0.0).text.strip()
        else:
            words = transcript.split()
            summary = " ".join(words[-max_words:])
        self._store.add_fact(
            "conversation", self.conversation_id, summary, kind="summary"
        )
        return summary
