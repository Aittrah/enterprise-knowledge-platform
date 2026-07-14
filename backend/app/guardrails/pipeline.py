"""GuardrailPipeline: the security layer's single entry point.

Input side runs before any retrieval or LLM call; output side runs on the
finished answer against the exact chunks that were retrieved for it.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from app.guardrails.groundedness import GroundednessReport, GroundednessValidator
from app.guardrails.injection import InjectionDetector, InputVerdict
from app.guardrails.pii import PIIDetector, PIIMatch
from app.prompts import verify_citations
from app.retrieval.base import RetrievedChunk

REFUSAL_TEXT = (
    "This request looks like an attempt to override the assistant's "
    "instructions, so it wasn't processed. Rephrase it as a question about "
    "your documents."
)


@dataclass
class OutputReport:
    groundedness: GroundednessReport
    invalid_citations: list[int] = field(default_factory=list)
    pii: list[PIIMatch] = field(default_factory=list)
    masked_text: str | None = None

    @property
    def trustworthy(self) -> bool:
        return self.groundedness.passed and not self.invalid_citations

    def to_dict(self) -> dict:
        return {
            "groundedness_score": self.groundedness.score,
            "unsupported_sentences": self.groundedness.unsupported_sentences,
            "invalid_citations": self.invalid_citations,
            "pii_found": [
                {"type": m.type, "masked": m.masked} for m in self.pii
            ],
            "trustworthy": self.trustworthy,
        }


class GuardrailPipeline:
    def __init__(
        self,
        injection: InjectionDetector | None = None,
        pii: PIIDetector | None = None,
        groundedness: GroundednessValidator | None = None,
        mask_pii: bool = True,
    ) -> None:
        self._injection = injection or InjectionDetector()
        self._pii = pii or PIIDetector()
        self._groundedness = groundedness or GroundednessValidator()
        self._mask_pii = mask_pii

    def screen_input(self, question: str) -> InputVerdict:
        return self._injection.screen(question)

    def screen_output(
        self, answer: str, chunks: list[RetrievedChunk]
    ) -> OutputReport:
        source_texts = [chunk.text for chunk in chunks]
        groundedness = self._groundedness.validate(answer, source_texts)
        invalid = verify_citations(answer, {i + 1 for i in range(len(chunks))})

        masked_text = None
        pii_matches: list[PIIMatch] = []
        if self._mask_pii:
            masked, pii_matches = self._pii.mask(answer)
            if pii_matches:
                masked_text = masked

        return OutputReport(
            groundedness=groundedness,
            invalid_citations=invalid,
            pii=pii_matches,
            masked_text=masked_text,
        )


def input_verdict_dict(verdict: InputVerdict) -> dict:
    return asdict(verdict)
