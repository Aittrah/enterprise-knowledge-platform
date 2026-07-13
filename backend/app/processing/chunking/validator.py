"""Chunk validation: catch bad chunk sets before they cost embedding money

or poison retrieval."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.ingestion.models import ExtractedDocument
from app.processing.chunking.models import Chunk

_REQUIRED_METADATA = ("source", "strategy")


@dataclass
class ValidationReport:
    ok: bool = True
    issues: list[str] = field(default_factory=list)
    stats: dict = field(default_factory=dict)

    def add(self, issue: str) -> None:
        self.ok = False
        self.issues.append(issue)


class ChunkValidator:
    def __init__(
        self,
        min_tokens: int = 10,
        max_tokens: int = 512,
        size_tolerance: float = 1.1,
        min_coverage: float = 0.7,
    ) -> None:
        self.min_tokens = min_tokens
        self.max_tokens = max_tokens
        self.size_tolerance = size_tolerance
        self.min_coverage = min_coverage

    def validate(
        self, chunks: list[Chunk], document: ExtractedDocument | None = None
    ) -> ValidationReport:
        report = ValidationReport()
        if not chunks:
            report.add("no chunks were produced")
            return report

        hard_limit = int(self.max_tokens * self.size_tolerance)
        seen: dict[str, int] = {}
        for chunk in chunks:
            label = f"chunk {chunk.index}"
            if not chunk.text.strip():
                report.add(f"{label}: empty text")
                continue
            if chunk.token_count > hard_limit and not chunk.keep_whole:
                report.add(
                    f"{label}: {chunk.token_count} tokens exceeds limit {hard_limit}"
                )
            if chunk.token_count < self.min_tokens and len(chunks) > 1:
                report.add(f"{label}: only {chunk.token_count} tokens")
            for key in _REQUIRED_METADATA:
                if not chunk.metadata.get(key):
                    report.add(f"{label}: missing metadata '{key}'")
            if chunk.text in seen:
                report.add(f"{label}: duplicate of chunk {seen[chunk.text]}")
            else:
                seen[chunk.text] = chunk.index

        if [c.index for c in chunks] != list(range(len(chunks))):
            report.add("chunk indices are not contiguous from 0")

        if document is not None and document.text:
            unique_chars = sum(len(text) for text in seen)
            coverage = min(1.0, unique_chars / len(document.text))
            report.stats["coverage"] = round(coverage, 3)
            if coverage < self.min_coverage:
                report.add(
                    f"chunks cover only {coverage:.0%} of the source text "
                    f"(minimum {self.min_coverage:.0%})"
                )

        tokens = [c.token_count for c in chunks]
        report.stats.update(
            chunks=len(chunks),
            avg_tokens=round(sum(tokens) / len(tokens), 1),
            max_tokens=max(tokens),
            min_tokens=min(tokens),
        )
        return report
