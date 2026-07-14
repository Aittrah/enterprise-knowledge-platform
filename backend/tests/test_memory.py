from pathlib import Path

import pytest

from app.agents.llm import LLMReply
from app.memory import MemoryService, MemoryStore


@pytest.fixture
def service(tmp_path: Path) -> MemoryService:
    return MemoryService(tmp_path / "memory.db")


# --- conversation memory --------------------------------------------------------


def test_messages_persist_across_instances(tmp_path: Path):
    db = tmp_path / "memory.db"
    MemoryService(db).conversation("c1").add("user", "hello")
    reloaded = MemoryService(db).conversation("c1")
    history = reloaded.history()
    assert [(m.role, m.content) for m in history] == [("user", "hello")]
    assert history[0].created_at  # timestamped


def test_history_keeps_order_and_conversations_are_isolated(service):
    c1, c2 = service.conversation("c1"), service.conversation("c2")
    c1.add("user", "first")
    c1.add("assistant", "second")
    c2.add("user", "other convo")
    assert [m.content for m in c1.history()] == ["first", "second"]
    assert [m.content for m in c2.history()] == ["other convo"]
    assert service.conversations() == ["c2", "c1"]  # most recent first


def test_context_window_trims_oldest_first(service):
    convo = service.conversation("c1")
    for i in range(10):
        convo.add("user", f"message number {i} with some padding words here")
    window = convo.context_window(max_tokens=30)
    assert 0 < len(window) < 10
    assert window[-1]["content"].startswith("message number 9")  # newest survives
    assert [m["content"] for m in window] == sorted(
        (m["content"] for m in window),
        key=lambda c: int(c.split()[2]),
    )


def test_context_window_always_returns_latest_message_even_if_over_budget(service):
    convo = service.conversation("c1")
    convo.add("user", "word " * 500)
    assert len(convo.context_window(max_tokens=10)) == 1


def test_summarize_with_llm_stores_summary_fact(service):
    class FakeLLM:
        name = "fake"

        def chat(self, messages, temperature=0.2):
            assert "Summarize" in messages[0]["content"]
            return LLMReply(text="User asked about leave; answer was 22 days.")

    convo = service.conversation("c1")
    convo.add("user", "How many leave days?")
    convo.add("assistant", "22 days [1].")
    summary = convo.summarize_to_long_term(llm=FakeLLM())

    assert summary == "User asked about leave; answer was 22 days."
    stored = service.recall("conversation", "c1")
    assert stored[0].kind == "summary"
    assert "22 days" in stored[0].content


def test_summarize_without_llm_falls_back_to_tail(service):
    convo = service.conversation("c1")
    convo.add("user", "alpha beta gamma")
    summary = convo.summarize_to_long_term(llm=None, max_words=2)
    assert summary == "beta gamma"


def test_summarize_empty_conversation_is_noop(service):
    assert service.conversation("empty").summarize_to_long_term() == ""
    assert service.recall("conversation", "empty") == []


# --- fact memory (user / project) ---------------------------------------------------


def test_remember_recall_ranked_by_relevance(service):
    service.remember("user", "u1", "Prefers answers as bullet points")
    service.remember("user", "u1", "Works in the Karachi office")
    service.remember("user", "u1", "Interested in annual leave policy changes")

    top = service.recall("user", "u1", "leave policy", limit=2)
    assert "annual leave policy" in top[0].content
    assert all("Karachi" not in f.content for f in top)


def test_recall_without_query_returns_most_recent(service):
    for i in range(6):
        service.remember("user", "u1", f"fact {i}")
    recent = service.recall("user", "u1", limit=3)
    assert [f.content for f in recent] == ["fact 3", "fact 4", "fact 5"]


def test_scopes_are_isolated(service):
    service.remember("user", "u1", "user fact")
    service.remember("project", "p1", "project fact")
    assert [f.content for f in service.recall("user", "u1")] == ["user fact"]
    assert [f.content for f in service.recall("project", "p1")] == ["project fact"]
    assert service.recall("user", "p1") == []


def test_invalid_scope_rejected(service):
    with pytest.raises(ValueError, match="scope"):
        service.remember("galaxy", "g1", "nope")


def test_forget_deletes_fact(service):
    fact_id = service.remember("user", "u1", "temporary")
    assert service.forget(fact_id)
    assert service.recall("user", "u1") == []
    assert not service.forget(fact_id)  # already gone


def test_digest_combines_relevant_scopes(service):
    service.remember("user", "u1", "Prefers bullet points")
    service.remember("project", "p1", "Project deadline is 2026-09-01")
    digest = service.digest("deadline bullet", user_id="u1", project_id="p1")
    assert "About this user:" in digest
    assert "Prefers bullet points" in digest
    assert "Project context:" in digest
    assert "2026-09-01" in digest
    assert service.digest("unrelated query zzz", user_id="u1") == ""


def test_store_close_releases_file(tmp_path: Path):
    store = MemoryStore(tmp_path / "m.db")
    store.add_message("c", "user", "x")
    store.close()
