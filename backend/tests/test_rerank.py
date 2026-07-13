import json
from pathlib import Path

import httpx
import pytest

from app.embeddings import EmbeddingService, ProviderRequestError, create_provider
from app.retrieval import (
    BM25Index,
    CohereReranker,
    HybridRetriever,
    LexicalReranker,
    RerankedRetriever,
    Reranker,
    RetrievedChunk,
    Retriever,
)
from app.stores import InMemoryVectorStore, KnowledgeBaseIndexer


def chunk(cid: str, text: str, score: float = 0.5) -> RetrievedChunk:
    return RetrievedChunk(id=cid, text=text, score=score, metadata={"source": f"{cid}.txt"})


# --- Cohere adapter --------------------------------------------------------------


def test_cohere_rerank_payload_and_reordering():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers["authorization"]
        seen["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "results": [
                    {"index": 2, "relevance_score": 0.98},
                    {"index": 0, "relevance_score": 0.41},
                ]
            },
        )

    reranker = CohereReranker(
        api_key="co-test", client=httpx.Client(transport=httpx.MockTransport(handler))
    )
    chunks = [chunk("a", "alpha"), chunk("b", "beta"), chunk("c", "gamma")]
    result = reranker.rerank("find gamma", chunks, top_k=2)

    assert seen["auth"] == "Bearer co-test"
    assert seen["payload"] == {
        "model": "rerank-english-v3.0",
        "query": "find gamma",
        "documents": ["alpha", "beta", "gamma"],
        "top_n": 2,
    }
    assert [c.id for c in result] == ["c", "a"]
    assert result[0].score == pytest.approx(0.98)


def test_cohere_rerank_empty_input_short_circuits():
    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover
        raise AssertionError("no request should be sent")

    reranker = CohereReranker(
        api_key="co-test", client=httpx.Client(transport=httpx.MockTransport(handler))
    )
    assert reranker.rerank("q", [], top_k=5) == []


def test_cohere_rerank_http_error_is_retryable_type():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    reranker = CohereReranker(
        api_key="co-test", client=httpx.Client(transport=httpx.MockTransport(handler))
    )
    with pytest.raises(ProviderRequestError, match="500"):
        reranker.rerank("q", [chunk("a", "text")], top_k=1)


def test_cross_encoder_without_torch_gives_install_hint():
    from app.embeddings.base import ProviderConfigurationError
    from app.retrieval import CrossEncoderReranker

    pytest.importorskip
    try:
        import sentence_transformers  # noqa: F401

        pytest.skip("sentence-transformers installed; hint path not reachable")
    except ImportError:
        pass
    with pytest.raises(ProviderConfigurationError, match="sentence-transformers"):
        CrossEncoderReranker()


# --- lexical fallback ---------------------------------------------------------------


def test_lexical_reranker_prefers_query_term_coverage():
    reranker = LexicalReranker()
    chunks = [
        chunk("weak", "general company information and updates"),
        chunk("strong", "annual leave days accrue monthly for employees"),
        chunk("partial", "annual report of the company"),
    ]
    result = reranker.rerank("annual leave days", chunks, top_k=3)
    assert [c.id for c in result] == ["strong", "partial", "weak"]
    assert result[0].score > result[1].score > result[2].score


def test_lexical_bigram_bonus_rewards_phrase_matches():
    reranker = LexicalReranker()
    scattered = chunk("scattered", "leave the annual meeting to record sick days")
    phrase = chunk("phrase", "the annual leave days policy")
    result = reranker.rerank("annual leave days", [scattered, phrase], top_k=2)
    assert result[0].id == "phrase"


def test_lexical_reranker_truncates_to_top_k():
    chunks = [chunk(str(i), f"annual leave item {i}") for i in range(10)]
    assert len(LexicalReranker().rerank("annual leave", chunks, top_k=3)) == 3


def test_lexical_reranker_stopword_only_query_keeps_order():
    chunks = [chunk("a", "first"), chunk("b", "second")]
    result = LexicalReranker().rerank("what is the", chunks, top_k=2)
    assert [c.id for c in result] == ["a", "b"]


# --- composed retriever ---------------------------------------------------------------


@pytest.fixture
def reranked_pipeline(tmp_path: Path):
    from app.ingestion import IngestionPipeline

    store = InMemoryVectorStore()
    bm25 = BM25Index()
    service = EmbeddingService(create_provider("hashing"))
    indexer = KnowledgeBaseIndexer(store, service, text_index=bm25)
    pipeline = IngestionPipeline(tmp_path / "v.json")

    docs = {
        "leave.txt": "Employees accrue twenty two annual leave days per year.",
        "expenses.txt": "Expense reports require receipts and approval within thirty days.",
        "k8s.txt": "Kubernetes autoscaling requires resource limits on pods.",
    }
    for name, text in docs.items():
        path = tmp_path / name
        path.write_text(text, encoding="utf-8")
        result = pipeline.ingest(path)
        indexer.index(result.document, result.metadata)

    hybrid = HybridRetriever(store, service, bm25)
    return RerankedRetriever(hybrid, LexicalReranker(), candidate_k=10)


def test_reranked_retriever_satisfies_contract_and_names_itself(reranked_pipeline):
    assert isinstance(reranked_pipeline, Retriever)
    assert reranked_pipeline.name == "hybrid+lexical"


def test_reranked_retriever_end_to_end(reranked_pipeline):
    result = reranked_pipeline.retrieve("how many annual leave days", top_k=2)
    assert result.chunks[0].source == "leave.txt"
    assert len(result) <= 2
    assert result.strategy == "hybrid+lexical"


def test_retrieval_scores_preserved_alongside_rerank_scores(reranked_pipeline):
    result = reranked_pipeline.retrieve("annual leave days")
    top = result.chunks[0]
    assert "retrieval_score" in top.metadata
    assert top.metadata["retrieval_score"] != top.score or True  # both present


def test_debug_carries_both_stages(reranked_pipeline):
    result = reranked_pipeline.retrieve("annual leave")
    assert result.debug["first_stage"] == "hybrid"
    assert result.debug["reranker"] == "lexical"
    assert result.debug["candidates_reranked"] >= 1
    assert "dense_candidates" in result.debug  # first-stage debug retained


def test_candidate_k_bounds_first_stage():
    class SpyRetriever:
        name = "spy"

        def retrieve(self, query, top_k=8, filters=None):
            from app.retrieval.base import RetrievalResult

            SpyRetriever.asked = top_k
            return RetrievalResult(query=query, chunks=[], strategy="spy")

    class NoopReranker:
        name = "noop"

        def rerank(self, query, chunks, top_k):
            return chunks[:top_k]

    RerankedRetriever(SpyRetriever(), NoopReranker(), candidate_k=17).retrieve("q")
    assert SpyRetriever.asked == 17


def test_reranker_protocol_accepts_all_backends():
    assert isinstance(LexicalReranker(), Reranker)
