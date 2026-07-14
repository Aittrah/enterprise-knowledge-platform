"""Groundedness validation: is each claim in the answer supported by the

retrieved sources?

Sentence-level lexical support scoring — deterministic, offline, cheap.
An LLM-judge scorer can replace `_support()` behind the same report shape
when a key is configured (noted for M22 evaluation too).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_SENTENCES = re.compile(r"(?<=[.!?])\s+")
_WORDS = re.compile(r"[a-z0-9][\w-]*")
_CITATION = re.compile(r"\[\d+\]")
_STOP = frozenset(
    "the a an and or of to in for on at by is are was were be been do does did "
    "how what when where why who which with from that this these those it its "
    "as not no can could would should will may might have has had you your we "
    "our they their he she his her most relevant passages extractive mode "
    "configure llm api key synthesized answers based indexed documents".split()
)

_SUPPORT_THRESHOLD = 0.5
_MIN_CONTENT_WORDS = 4  # shorter sentences carry no checkable claim


@dataclass
class GroundednessReport:
    score: float  # 0..1 share of supported claim-sentences
    supported: int = 0
    unsupported: int = 0
    unsupported_sentences: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.unsupported == 0


def _content_words(text: str) -> set[str]:
    return {w for w in _WORDS.findall(text.lower()) if w not in _STOP and len(w) > 2}


class GroundednessValidator:
    def __init__(self, support_threshold: float = _SUPPORT_THRESHOLD) -> None:
        self._threshold = support_threshold

    def validate(self, answer: str, source_texts: list[str]) -> GroundednessReport:
        source_words = [_content_words(text) for text in source_texts]
        report = GroundednessReport(score=1.0)
        clean = _CITATION.sub("", answer)

        for sentence in _SENTENCES.split(clean):
            words = _content_words(sentence)
            if len(words) < _MIN_CONTENT_WORDS:
                continue
            support = max(
                (len(words & source) / len(words) for source in source_words),
                default=0.0,
            )
            if support >= self._threshold:
                report.supported += 1
            else:
                report.unsupported += 1
                report.unsupported_sentences.append(sentence.strip()[:200])

        total = report.supported + report.unsupported
        report.score = round(report.supported / total, 3) if total else 1.0
        return report
