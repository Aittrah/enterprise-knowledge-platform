from pathlib import Path

import pytest

from app.embeddings import EmbeddingService, create_provider
from app.retrieval import DenseRetriever, RetrievalResult, Retriever
from app.stores import InMemoryVectorStore, KnowledgeBaseIndexer


@pytest.fixture
def corpus(tmp_path: Path):
    """Three documents indexed into an in-memory store (offline stack)."""
    from app.ingestion import IngestionPipeline

    store = InMemoryVectorStore()
    service = EmbeddingService(create_provider("hashing"))
    indexer = KnowledgeBaseIndexer(store, service)
    pipeline = IngestionPipeline(tmp_path / "v.json")

    docs = {
        "leave.txt": "Employees accrue twenty two annual leave days per year. "
        "Unused annual leave days carry over to the next year.",
        "expenses.txt": "Travel expense reports require receipts and manager approval "
        "within thirty days of the trip.",
        "k8s.txt": "Kubernetes cluster autoscaling requires resource limits and "
        "readiness probes on every pod.",
    }
    for name, text in docs.items():
        path = tmp_path / name
        path.write_text(text, encoding="utf-8")
        result = pipeline.ingest(path)
        indexer.index(result.document, result.metadata)

    return store, service


def test_dense_retriever_satisfies_the_retriever_contract(corpus):
    store, service = corpus
    assert isinstance(DenseRetriever(store, service), Retriever)


def test_relevant_document_ranks_first(corpus):
    store, service = corpus
    retriever = DenseRetriever(store, service, min_score=0.0)
    result = retriever.retrieve("how many annual leave days do employees get")
    assert isinstance(result, RetrievalResult)
    assert result.chunks[0].source == "leave.txt"
    assert result.strategy == "dense"
    assert result.elapsed_ms >= 0


def test_scores_are_ordered_descending(corpus):
    store, service = corpus
    result = DenseRetriever(store, service, min_score=0.0).retrieve("expense receipts")
    scores = [c.score for c in result.chunks]
    assert scores == sorted(scores, reverse=True)


def test_similarity_threshold_drops_noise(corpus):
    store, service = corpus
    strict = DenseRetriever(store, service, min_score=0.35)
    result = strict.retrieve("annual leave days carry over")
    assert all(c.score >= 0.35 for c in result.chunks)
    assert result.debug["below_threshold"] >= 1
    assert result.debug["candidates"] == len(result) + result.debug["below_threshold"]


def test_metadata_filters_scope_the_search(corpus):
    store, service = corpus
    retriever = DenseRetriever(store, service, min_score=0.0)
    result = retriever.retrieve("approval process", filters={"source": "expenses.txt"})
    assert result.chunks and all(c.source == "expenses.txt" for c in result.chunks)


def test_top_k_limits_results(corpus):
    store, service = corpus
    result = DenseRetriever(store, service, min_score=0.0).retrieve("policy", top_k=2)
    assert len(result) <= 2


def test_empty_store_returns_empty_result(tmp_path: Path):
    service = EmbeddingService(create_provider("hashing"))
    retriever = DenseRetriever(InMemoryVectorStore(), service)
    result = retriever.retrieve("anything")
    assert len(result) == 0 and result.sources == []


def test_query_uses_query_side_embedding(corpus):
    """Retrieval must embed with input_type='query' (E5/BGE correctness)."""
    calls: list[str] = []

    class SpyProvider:
        name, model, dimension = "spy", "v1", 4

        def embed(self, texts, input_type="document"):
            calls.append(input_type)
            return [[1.0, 0.0, 0.0, 0.0] for _ in texts]

    retriever = DenseRetriever(InMemoryVectorStore(), EmbeddingService(SpyProvider()))
    retriever.retrieve("query text")
    assert calls == ["query"]


def test_similar_finds_related_chunks_and_excludes_self(corpus):
    store, service = corpus
    retriever = DenseRetriever(store, service)
    anchor = retriever.retrieve("annual leave days", top_k=1).chunks[0]
    related = retriever.similar(anchor.text, top_k=3, exclude_id=anchor.id)
    assert all(chunk.id != anchor.id for chunk in related)
    assert related, "related passages should be returned"


def test_sources_deduplicate_in_order(corpus):
    store, service = corpus
    result = DenseRetriever(store, service, min_score=0.0).retrieve(
        "annual leave and expense receipts", top_k=6
    )
    assert len(result.sources) == len(set(result.sources))
