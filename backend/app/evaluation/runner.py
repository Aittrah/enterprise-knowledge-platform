"""EvaluationRunner: golden dataset -> retrieval and answer quality reports.

Faithfulness reuses the M20 groundedness validator, so evaluation and
runtime guardrails measure hallucination the same way; hallucination rate
is its complement.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.agents.orchestrator import AgentOrchestrator
from app.evaluation.dataset import GoldenDataset
from app.evaluation.metrics import (
    hit_rate,
    percentile,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)
from app.guardrails.groundedness import GroundednessValidator
from app.prompts import parse_citations
from app.retrieval.base import Retriever


@dataclass
class RetrievalReport:
    dataset: str
    k: int
    cases: list[dict] = field(default_factory=list)
    aggregates: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "dataset": self.dataset,
            "k": self.k,
            "aggregates": self.aggregates,
            "cases": self.cases,
        }


@dataclass
class AnswerReport:
    dataset: str
    cases: list[dict] = field(default_factory=list)
    aggregates: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"dataset": self.dataset, "aggregates": self.aggregates, "cases": self.cases}


def _mean(values: list[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0


class EvaluationRunner:
    def __init__(
        self,
        retriever: Retriever,
        orchestrator: AgentOrchestrator | None = None,
        groundedness: GroundednessValidator | None = None,
    ) -> None:
        self._retriever = retriever
        self._orchestrator = orchestrator
        self._groundedness = groundedness or GroundednessValidator()

    # -- retrieval quality ---------------------------------------------------------

    def evaluate_retrieval(self, dataset: GoldenDataset, k: int = 5) -> RetrievalReport:
        report = RetrievalReport(dataset=dataset.name, k=k)
        latencies: list[float] = []
        for case in dataset.cases:
            result = self._retriever.retrieve(case.question, top_k=k)
            ranked = [chunk.source for chunk in result.chunks]
            relevant = set(case.relevant_sources)
            latencies.append(result.elapsed_ms)
            report.cases.append(
                {
                    "question": case.question,
                    "retrieved": ranked,
                    "precision": round(precision_at_k(ranked, relevant, k), 4),
                    "recall": round(recall_at_k(ranked, relevant, k), 4),
                    "mrr": round(reciprocal_rank(ranked, relevant), 4),
                    "hit": hit_rate(ranked, relevant, k),
                    "latency_ms": result.elapsed_ms,
                }
            )
        report.aggregates = {
            "context_precision": _mean([c["precision"] for c in report.cases]),
            "context_recall": _mean([c["recall"] for c in report.cases]),
            "mrr": _mean([c["mrr"] for c in report.cases]),
            "hit_rate": _mean([c["hit"] for c in report.cases]),
            "latency_p50_ms": percentile(latencies, 50),
            "latency_p95_ms": percentile(latencies, 95),
        }
        return report

    # -- answer quality ------------------------------------------------------------------

    def evaluate_answers(self, dataset: GoldenDataset) -> AnswerReport:
        if self._orchestrator is None:
            raise ValueError("evaluate_answers needs an orchestrator")
        report = AnswerReport(dataset=dataset.name)
        for case in dataset.cases:
            answer = self._orchestrator.ask(case.question, agent_id=case.agent_id)
            grounded = self._groundedness.validate(
                answer.text, [chunk.text for chunk in answer.chunks]
            )
            cited = parse_citations(answer.text)
            valid_cited = [c["n"] for c in answer.citations]
            citation_accuracy = (
                len(valid_cited) / len(cited) if cited else 0.0
            )
            text = answer.text.lower()
            keyword_coverage = (
                sum(1 for kw in case.expected_keywords if kw.lower() in text)
                / len(case.expected_keywords)
                if case.expected_keywords
                else 1.0
            )
            report.cases.append(
                {
                    "question": case.question,
                    "agent": answer.agent_id,
                    "faithfulness": grounded.score,
                    "citation_accuracy": round(citation_accuracy, 4),
                    "keyword_coverage": round(keyword_coverage, 4),
                    "grounded": answer.grounded,
                    "unsupported": grounded.unsupported_sentences,
                }
            )
        faithfulness = _mean([c["faithfulness"] for c in report.cases])
        report.aggregates = {
            "faithfulness": faithfulness,
            "hallucination_rate": round(1 - faithfulness, 4),
            "citation_accuracy": _mean([c["citation_accuracy"] for c in report.cases]),
            "keyword_coverage": _mean([c["keyword_coverage"] for c in report.cases]),
            "grounded_share": _mean(
                [1.0 if c["grounded"] else 0.0 for c in report.cases]
            ),
        }
        return report
