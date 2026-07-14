"""Memory system: conversation, user, project, and long-term memory.

    from app.memory import MemoryService

    memory = MemoryService(Path("data/memory.db"))
    convo = memory.conversation("conv-1")
    convo.add("user", "How many leave days do I get?")
    convo.context_window(max_tokens=2000)      # trimmed history for the prompt

    memory.remember("user", "u-42", "Prefers answers in bullet points")
    memory.recall("user", "u-42", "answer format")   # relevant facts
"""

from app.memory.conversation import ConversationMemory
from app.memory.service import MemoryService
from app.memory.store import MemoryStore, StoredFact, StoredMessage

__all__ = [
    "ConversationMemory",
    "MemoryService",
    "MemoryStore",
    "StoredFact",
    "StoredMessage",
]
