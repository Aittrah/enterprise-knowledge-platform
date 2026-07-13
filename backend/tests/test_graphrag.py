from pathlib import Path

import pytest

from app.embeddings import EmbeddingService, create_provider
from app.graph import GraphBuilder, InMemoryGraphStore
from app.retrieval import BM25Index, GraphRAGRetriever, HybridRetriever, Retriever
from app.stores import InMemoryVectorStore, KnowledgeBaseIndexer


@pytest.fixture
def graphrag_env(tmp_path: Path):
    """Corpus where the connection between Sara Khan and the budget doc is
    only knowable through the graph: the budget document never names her."""
    from app.ingestion import IngestionPipeline

    store = InMemoryVectorStore()
    bm25 = BM25Index()
    graph = InMemoryGraphStore()
    service = EmbeddingService(create_provider("hashing"))
    indexer = KnowledgeBaseIndexer(store, service, text_index=bm25)
    graph_builder = GraphBuilder(graph)
    pipeline = IngestionPipeline(tmp_path / "v.json")

    docs = {
        "team.txt": "Ms. Sara Khan works in the Finance department. "
        "Sara Khan reports to Bilal Ahmed.",
        "budget.txt": "The Finance department budget for travel is capped at "
        "$40,000.00 for the fiscal year.",
        "k8s.txt": "Kubernetes cluster autoscaling requires resource limits "
        "and readiness probes on every pod.",
    }
    for name, text in docs.items():
        path = tmp_path / name
        path.write_text(text, encoding="utf-8")
        result = pipeline.ingest(path)
        indexer.index(result.document, result.metadata)
        graph_builder.build(result.document, result.metadata)

    hybrid = HybridRetriever(store, service, bm25)
    return GraphRAGRetriever(hybrid, graph), graph


def test_graphrag_satisfies_retriever_contract(graphrag_env):
    retriever, _ = graphrag_env
    assert isinstance(retriever, Retriever)


def test_graph_connects_person_to_documents_vector_search_would_miss(graphrag_env):
    retriever, _ = graphrag_env
    result = retriever.retrieve("What budget applies to Sara Khan?", top_k=4)
    sources = result.sources
    assert "team.txt" in sources  # where Sara appears
    assert "budget.txt" in sources  # linked via Finance department in the graph
    assert "budget.txt" in result.debug["graph_documents"]


def test_debug_exposes_graph_reasoning(graphrag_env):
    retriever, _ = graphrag_env
    result = retriever.retrieve("Who does Sara Khan report to?")
    assert "Sara Khan" in result.debug["matched_entities"]
    assert any(r["type"] == "REPORTS_TO" for r in result.debug["graph_context"])
    evidence = [r["evidence"] for r in result.debug["graph_context"]]
    assert any("reports to" in e.lower() for e in evidence)


def test_related_entities_are_collected(graphrag_env):
    retriever, _ = graphrag_env
    result = retriever.retrieve("Sara Khan travel spending")
    related = result.debug["related_entities"]
    assert "Finance" in related or "Bilal Ahmed" in related


def test_queries_without_graph_matches_fall_back_to_vector_leg(graphrag_env):
    retriever, _ = graphrag_env
    result = retriever.retrieve("readiness probes for autoscaling pods")
    assert result.chunks[0].source == "k8s.txt"
    assert result.debug["graph_candidates"] == 0
    assert result.debug["vector_candidates"] > 0


def test_scores_normalized_and_fusion_ranks_attached(graphrag_env):
    retriever, _ = graphrag_env
    result = retriever.retrieve("Sara Khan Finance budget")
    assert result.chunks[0].score == 1.0
    assert "fusion_ranks" in result.chunks[0].metadata


def test_lowercase_mentions_still_seed_the_graph(graphrag_env):
    retriever, _ = graphrag_env
    # No capitalized entities for the extractor; falls back to node search.
    result = retriever.retrieve("what is the finance travel budget")
    assert "budget.txt" in result.debug["graph_documents"]
