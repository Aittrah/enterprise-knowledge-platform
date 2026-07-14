from pathlib import Path

import pytest

from app.agents import AgentOrchestrator
from app.agents.llm import LLMReply
from app.embeddings import EmbeddingService, create_provider
from app.evaluation import (
    EvalCase,
    EvaluationRunner,
    GoldenDataset,
    hit_rate,
    percentile,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)
from app.retrieval import BM25Index, HybridRetriever
from app.stores import InMemoryVectorStore, KnowledgeBaseIndexer


# --- metric math -----------------------------------------------------------------


def test_precision_recall_mrr_hit():
    ranked = ["a", "b", "c", "d"]
    relevant = {"b", "d", "z"}
    assert precision_at_k(ranked, relevant, 2) == 0.5  # a,b -> b relevant
    assert recall_at_k(ranked, relevant, 4) == pytest.approx(2 / 3)
    assert reciprocal_rank(ranked, relevant) == 0.5  # first hit at rank 2
    assert hit_rate(ranked, relevant, 1) == 0.0
    assert hit_rate(ranked, relevant, 2) == 1.0


def test_metric_edge_cases():
    assert precision_at_k([], {"a"}, 5) == 0.0
    assert recall_at_k(["a"], set(), 5) == 1.0  # nothing to find
    assert reciprocal_rank(["x"], {"a"}) == 0.0
    assert percentile([], 95) == 0.0
    assert percentile([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 50) == 5
    assert percentile([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 95) == 10


# --- dataset ---------------------------------------------------------------------------


def test_dataset_roundtrip(tmp_path: Path):
    dataset = GoldenDataset(
        name="smoke",
        cases=[EvalCase(question="q1", relevant_sources=["a.txt"], expected_keywords=["leave"])],
    )
    path = tmp_path / "golden.json"
    dataset.save(path)
    loaded = GoldenDataset.load(path)
    assert loaded.name == "smoke"
    assert loaded.cases[0].question == "q1"
    assert len(loaded) == 1


# --- runner (offline stack) ----------------------------------------------------------------


class ScriptedLLM:
    name, model = "scripted", "extractive"

    def chat(self, messages, temperature=0.2):
        # Faithful, cited answer echoing source content.
        return LLMReply(
            text="Employees accrue twenty two annual leave days per year [1].",
            prompt_tokens=50,
            completion_tokens=15,
        )


@pytest.fixture
def eval_env(tmp_path: Path):
    from app.ingestion import IngestionPipeline

    store = InMemoryVectorStore()
    bm25 = BM25Index()
    service = EmbeddingService(create_provider("hashing"))
    indexer = KnowledgeBaseIndexer(store, service, text_index=bm25)
    pipeline = IngestionPipeline(tmp_path / "v.json")
    docs = {
        "leave.txt": "Employees accrue twenty two annual leave days per year.",
        "expenses.txt": "Expense reports require receipts within thirty days.",
        "k8s.txt": "Kubernetes autoscaling requires resource limits on pods.",
    }
    for name, text in docs.items():
        path = tmp_path / name
        path.write_text(text, encoding="utf-8")
        result = pipeline.ingest(path)
        indexer.index(result.document, result.metadata)

    retriever = HybridRetriever(store, service, bm25)
    dataset = GoldenDataset(
        name="hr-smoke",
        cases=[
            EvalCase(
                question="How many annual leave days do employees get?",
                relevant_sources=["leave.txt"],
                expected_keywords=["twenty two", "leave"],
            ),
            EvalCase(
                question="What do expense reports require?",
                relevant_sources=["expenses.txt"],
            ),
        ],
    )
    return retriever, dataset


def test_retrieval_evaluation_report(eval_env):
    retriever, dataset = eval_env
    report = EvaluationRunner(retriever).evaluate_retrieval(dataset, k=3)
    agg = report.aggregates
    assert agg["hit_rate"] == 1.0  # both cases find their document
    assert agg["mrr"] == 1.0  # ...at rank 1
    assert 0 < agg["context_precision"] <= 1.0
    assert agg["context_recall"] == 1.0
    assert agg["latency_p95_ms"] >= agg["latency_p50_ms"] >= 0
    assert len(report.cases) == 2
    assert report.to_dict()["dataset"] == "hr-smoke"


def test_answer_evaluation_report(eval_env):
    retriever, dataset = eval_env
    orchestrator = AgentOrchestrator(retriever, ScriptedLLM())
    report = EvaluationRunner(retriever, orchestrator).evaluate_answers(dataset)
    agg = report.aggregates
    assert agg["faithfulness"] > 0.9
    assert agg["hallucination_rate"] == pytest.approx(1 - agg["faithfulness"])
    assert agg["citation_accuracy"] == 1.0
    assert 0 <= agg["grounded_share"] <= 1.0


def test_answer_evaluation_requires_orchestrator(eval_env):
    retriever, dataset = eval_env
    with pytest.raises(ValueError, match="orchestrator"):
        EvaluationRunner(retriever).evaluate_answers(dataset)
