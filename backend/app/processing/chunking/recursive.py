"""Recursive chunking: split on the largest structural separator that

produces fitting pieces (paragraph > line > sentence > word), then greedily
re-merge adjacent pieces up to the budget so chunks stay as large — and as
contextful — as the limit allows.
"""

from __future__ import annotations

import re

from app.processing.chunking.tokens import DEFAULT_COUNTER, TokenCounter

_SEPARATORS = ("\n\n", "\n", re.compile(r"(?<=[.!?])\s+"), " ")


class RecursiveChunker:
    name = "recursive"

    def __init__(
        self, max_tokens: int = 512, counter: TokenCounter = DEFAULT_COUNTER
    ) -> None:
        self.max_tokens = max_tokens
        self.counter = counter

    def split(self, text: str) -> list[str]:
        pieces = self._split(text.strip(), level=0)
        return [p for p in (piece.strip() for piece in pieces) if p]

    def _split(self, text: str, level: int) -> list[str]:
        if self.counter.count(text) <= self.max_tokens:
            return [text]
        if level >= len(_SEPARATORS):
            return [text]  # atomic and oversized; the validator will flag it

        separator = _SEPARATORS[level]
        parts = (
            separator.split(text)
            if isinstance(separator, re.Pattern)
            else text.split(separator)
        )
        if len(parts) == 1:
            return self._split(text, level + 1)

        joiner = " " if isinstance(separator, re.Pattern) else separator
        pieces: list[str] = []
        for part in parts:
            if not part.strip():
                continue
            pieces.extend(self._split(part, level + 1))
        return self._merge(pieces, joiner)

    def _merge(self, pieces: list[str], joiner: str) -> list[str]:
        merged: list[str] = []
        buffer = ""
        for piece in pieces:
            candidate = f"{buffer}{joiner}{piece}" if buffer else piece
            if buffer and self.counter.count(candidate) > self.max_tokens:
                merged.append(buffer)
                buffer = piece
            else:
                buffer = candidate
        if buffer:
            merged.append(buffer)
        return merged
