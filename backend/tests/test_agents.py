import json
from pathlib import Path

import httpx
import pytest

from app.agents import AgentOrchestrator, AgentRouter, LLMClient, LLMReply, OpenAICompatibleClient
from app.agents.roster import ROSTER
from app.embeddings import EmbeddingService, create_provider
from app.retrieval import BM25Index, HybridRetriever
from app.stores import InMemoryVectorStore, KnowledgeBaseIndexer


class FakeLLM:
    """Scripted LLM: returns queued replies and records every prompt."""

    name = "fake"

    def __init__(self, *replies: str):
        self._replies = list(replies)
        self.prompts: list[list[dict]] = []

    def chat(self, messages, temperature=0.2) -> LLMReply:
        self.prompts.append(messages)
        text = self._replies.pop(0) if self._replies else "[1] stub"
        return LLMReply(text=text, prompt_tokens=100, completion_tokens=20)


# --- OpenAI-compatible client -----------------------------------------------------


def test_openai_client_payload_and_parsing():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers["authorization"]
        seen["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "model": "gpt-4o-mini",
                "choices": [{"message": {"role": "assistant", "content": "Hi [1]."}}],
                "usage": {"prompt_tokens": 12, "completion_tokens": 3},
            },
        )

    client = OpenAICompatibleClient(
        api_key="sk-test", client=httpx.Client(transport=httpx.MockTransport(handler))
    )
    reply = client.chat([{"role": "user", "content": "hello"}], temperature=0.5)

    assert seen["auth"] == "Bearer sk-test"
    assert seen["payload"]["temperature"] == 0.5
    assert seen["payload"]["messages"][0]["content"] == "hello"
    assert reply.text == "Hi [1]."
    assert (reply.prompt_tokens, reply.completion_tokens) == (12, 3)
    assert isinstance(client, LLMClient)


# --- router ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "question,expected",
    [
        ("How many vacation days do employees get?", "hr"),
        ("Where is invoice INV-9987 in the budget?", "finance"),
        ("How do I deploy the kubernetes pipeline?", "developer"),
        ("What does the NDA clause say about liability?", "legal"),
        ("Tell me something interesting", "research"),  # default fallback
    ],
)
def test_keyword_router(question, expected):
    assert AgentRouter().route(question).id == expected


def test_llm_router_used_when_it_answers_a_known_id():
    router = AgentRouter(llm=FakeLLM("legal"))
    assert router.route("what about vacation days?").id == "legal"


def test_llm_router_falls_back_on_unknown_id_or_error():
    assert AgentRouter(llm=FakeLLM("astrologer")).route("vacation days?").id == "hr"

    class BrokenLLM:
        name = "broken"

        def chat(self, messages, temperature=0.2):
            raise RuntimeError("down")

    assert AgentRouter(llm=BrokenLLM()).route("vacation days?").id == "hr"


# --- agent answers (offline end-to-end) ---------------------------------------------------


@pytest.fixture
def orchestrator_env(tmp_path: Path):
    from app.ingestion import IngestionPipeline

    store = InMemoryVectorStore()
    bm25 = BM25Index()
    service = EmbeddingService(create_provider("hashing"))
    indexer = KnowledgeBaseIndexer(store, service, text_index=bm25)
    pipeline = IngestionPipeline(tmp_path / "v.json")

    docs = {
        "leave.txt": "Employees accrue twenty two annual leave days per year.",
        "budget.txt": "The travel budget is capped at $40,000.00 per fiscal year.",
    }
    for name, text in docs.items():
        path = tmp_path / name
        path.write_text(text, encoding="utf-8")
        result = pipeline.ingest(path)
        indexer.index(result.document, result.metadata)

    return HybridRetriever(store, service, bm25)


def test_agent_answer_is_cited_and_grounded(orchestrator_env):
    retriever = orchestrator_env
    llm = FakeLLM("Employees get twenty two days of annual leave [1].")
    orchestrator = AgentOrchestrator(retriever, llm)
    answer = orchestrator.ask("How many annual leave days do employees get?")

    assert answer.agent_id == "hr"  # routed by keywords
    assert answer.citations[0]["n"] == 1
    assert answer.citations[0]["source"] == "leave.txt"
    assert answer.citations[0]["chunk_id"]
    assert answer.grounded
    assert answer.invalid_citations == []
    assert answer.prompt_tokens == 100


def test_prompt_contains_numbered_sources_and_charter(orchestrator_env):
    retriever = orchestrator_env
    llm = FakeLLM("Answer [1].")
    AgentOrchestrator(retriever, llm).ask("annual leave days?", agent_id="hr")

    system = llm.prompts[0][0]["content"]
    user = llm.prompts[0][1]["content"]
    assert "HR Agent" in system
    assert "human resources" in system
    assert "[1] leave.txt" in user
    assert "annual leave days?" in user


def test_invented_citations_are_flagged_not_hidden(orchestrator_env):
    retriever = orchestrator_env
    llm = FakeLLM("Leave is 22 days [1] and pigs fly [9].")
    answer = AgentOrchestrator(retriever, llm).ask("leave days?", agent_id="hr")
    assert answer.invalid_citations == [9]
    assert not answer.grounded


def test_pinned_agent_overrides_routing(orchestrator_env):
    retriever = orchestrator_env
    answer = AgentOrchestrator(retriever, FakeLLM("x [1]")).ask(
        "annual leave days", agent_id="legal"
    )
    assert answer.agent_id == "legal"


def test_unknown_agent_id_raises(orchestrator_env):
    orchestrator = AgentOrchestrator(orchestrator_env, FakeLLM())
    with pytest.raises(ValueError, match="unknown agent 'astrologer'"):
        orchestrator.ask("q", agent_id="astrologer")


def test_roster_exposes_six_domain_agents():
    assert set(ROSTER) == {"hr", "finance", "research", "developer", "legal", "operations"}
    orchestrator = AgentOrchestrator(None, FakeLLM())
    assert len(orchestrator.agents) == 6
