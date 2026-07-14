"""Evaluation framework: measure retrieval and answer quality against a

golden dataset, offline and repeatably.

    dataset = GoldenDataset.load(Path("eval/golden.json"))
    runner = EvaluationRunner(retriever, orchestrator)
    retrieval_report = runner.evaluate_retrieval(dataset)
    answer_report = runner.evaluate_answers(dataset)
"""

from app.evaluation.dataset import EvalCase, GoldenDataset
from app.evaluation.metrics import (
    hit_rate,
    percentile,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)
from app.evaluation.runner import EvaluationRunner

__all__ = [
    "EvalCase",
    "EvaluationRunner",
    "GoldenDataset",
    "hit_rate",
    "percentile",
    "precision_at_k",
    "recall_at_k",
    "reciprocal_rank",
]
