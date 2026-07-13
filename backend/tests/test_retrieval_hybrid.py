from pathlib import Path

import pytest

from app.embeddings import EmbeddingService, create_provider
from app.retrieval import BM25Index, HybridRetriever, Retriever, reciprocal_rank_fusion
from app.stores import InMemoryVectorStore, KnowledgeBaseIndexer, VectorRecord


def rec(rid: str, text: str, **metadata) -> VectorRecord:
    return VectorRecord(id=rid, vector=[], text=text, metadata=metadata)


# --- BM25 ---------------------------------------------------------------------


def test_bm25_ranks_matching_terms():
    index = BM25Index()
    index.upsert(
        [
            rec("a", "annual leave policy for employees", source="hr.txt"),
            rec("b", "kubernetes deployment guide", source="ops.txt"),
        ]
    )
    hits = index.search("annual leave")
    assert hits[0].id == "a"
    assert len(hits) == 1  # no query term appears in b


def test_bm25_rare_terms_outweigh_common_ones():
    index = BM25Index()
    index.upsert(
        [
            rec("common1", "policy update for the policy team policy"),
            rec("common2", "policy review notes"),
            rec("rare", "policy INV-9987 reimbursement"),
        ]
    )
    hits = index.search("policy INV-9987")
    assert hits[0].id == "rare"


def test_bm25_is_case_insensitive_and_handles_ids():
    index = BM25Index()
    index.upsert([rec("a", "Invoice INV-9987 approved")])
    assert index.search("inv-9987")[0].id == "a"


def test_bm25_filters_and_delete():
    index = BM25Index()
    index.upsert(
        [
            rec("a", "leave policy", source="x.txt"),
            rec("b", "leave request", source="y.txt"),
        ]
    )
    assert [h.id for h in index.search("leave", filters={"source": "y.txt"})] == ["b"]
    index.delete_by_filter({"source": "x.txt"})
    assert len(index) == 1


def test_bm25_upsert_replaces_same_id():
    index = BM25Index()
    index.upsert([rec("a", "old text about cats")])
    index.upsert([rec("a", "new text about dogs")])
    assert index.search("cats") == []
    assert index.search("dogs")[0].id == "a"
    assert len(index) == 1


def test_bm25_empty_cases():
    index = BM25Index()
    assert index.search("anything") == []
    index.upsert([rec("a", "text")])
    assert index.search("") == []


# --- RRF -----------------------------------------------------------------------


def test_rrf_rewards_agreement():
    fused = reciprocal_rank_fusion(
        {"dense": ["a", "b", "c"], "bm25": ["b", "d", "a"]}, k=60
    )
    assert fused[0].id in {"a", "b"}  # items in both lists lead
    ids = [f.id for f in fused]
    assert ids.index("b") < ids.index("d")
    assert ids.index("a") < ids.index("c")


def test_rrf_records_contributing_ranks():
    fused = reciprocal_rank_fusion({"dense": ["a"], "bm25": ["b", "a"]})
    a = next(f for f in fused if f.id == "a")
    assert a.ranks == {"dense": 1, "bm25": 2}


def test_rrf_weights_bias_a_ranking():
    heavy_bm25 = reciprocal_rank_fusion(
        {"dense": ["a", "b"], "bm25": ["b", "a"]},
        weights={"dense": 1.0, "bm25": 3.0},
    )
    assert heavy_bm25[0].id == "b"


# --- hybrid engine -----------------------------------------------------------------


@pytest.fixture
def hybrid_env(tmp_path: Path):
    from app.ingestion import IngestionPipeline

    store = InMemoryVectorStore()
    bm25 = BM25Index()
    service = EmbeddingService(create_provider("hashing"))
    indexer = KnowledgeBaseIndexer(store, service, text_index=bm25)
    pipeline = IngestionPipeline(tmp_path / "v.json")

    docs = {
        "leave.txt": "Employees accrue twenty two annual leave days per year and "
        "unused annual leave days carry over.",
        "invoice.txt": "Invoice INV-9987 from Globex Corporation was approved for "
        "reimbursement by the finance team.",
        "k8s.txt": "Kubernetes cluster autoscaling requires resource limits and "
        "readiness probes on every pod.",
    }
    for name, text in docs.items():
        path = tmp_path / name
        path.write_text(text, encoding="utf-8")
        result = pipeline.ingest(path)
        indexer.index(result.document, result.metadata)

    retriever = HybridRetriever(store, service, bm25)
    return retriever, indexer, bm25, pipeline, tmp_path


def test_hybrid_satisfies_retriever_contract(hybrid_env):
    retriever, *_ = hybrid_env
    assert isinstance(retriever, Retriever)


def test_exact_identifier_queries_hit_via_bm25(hybrid_env):
    retriever, *_ = hybrid_env
    result = retriever.retrieve("INV-9987")
    assert result.chunks[0].source == "invoice.txt"
    assert result.chunks[0].metadata["fusion_ranks"].get("bm25") == 1


def test_semantic_queries_still_work(hybrid_env):
    retriever, *_ = hybrid_env
    result = retriever.retrieve("how many annual leave days do employees receive")
    assert result.chunks[0].source == "leave.txt"


def test_scores_normalized_and_descending(hybrid_env):
    retriever, *_ = hybrid_env
    result = retriever.retrieve("annual leave")
    assert result.chunks[0].score == 1.0
    scores = [c.score for c in result.chunks]
    assert scores == sorted(scores, reverse=True)


def test_filters_apply_to_both_legs(hybrid_env):
    retriever, *_ = hybrid_env
    result = retriever.retrieve("approved reimbursement", filters={"source": "k8s.txt"})
    assert all(c.source == "k8s.txt" for c in result.chunks)


def test_debug_reports_fusion_internals(hybrid_env):
    retriever, *_ = hybrid_env
    result = retriever.retrieve("annual leave days")
    assert result.strategy == "hybrid"
    assert result.debug["dense_candidates"] > 0
    assert result.debug["bm25_candidates"] > 0
    assert "overlap" in result.debug


def test_indexer_keeps_bm25_in_sync_on_reingestion(hybrid_env):
    retriever, indexer, bm25, pipeline, tmp_path = hybrid_env
    before = len(bm25)

    path = tmp_path / "invoice.txt"
    path.write_text(
        "Invoice INV-5555 replaces the previous one entirely.", encoding="utf-8"
    )
    result = pipeline.ingest(path)
    indexer.index(result.document, result.metadata)

    assert len(bm25) <= before  # old chunks superseded, not accumulated
    assert bm25.search("INV-9987") == []  # stale text unreachable by keyword
    stale = retriever.retrieve("INV-9987")
    assert all("INV-9987" not in c.text for c in stale.chunks)
    assert retriever.retrieve("INV-5555").chunks[0].source == "invoice.txt"
