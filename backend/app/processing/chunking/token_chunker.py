"""Token-window chunking: fixed-size sliding window with overlap.

The baseline strategy — ignores structure, never produces oversized
chunks, and its overlap guarantees no fact is lost on a boundary.
"""

from __future__ import annotations

import re

from app.processing.chunking.tokens import DEFAULT_COUNTER, TokenCounter

_TOKEN_SPAN = re.compile(r"\w+|[^\w\s]")


class TokenChunker:
    name = "token"

    def __init__(
        self,
        max_tokens: int = 512,
        overlap: int = 64,
        counter: TokenCounter = DEFAULT_COUNTER,
    ) -> None:
        if not 0 <= overlap < max_tokens:
            raise ValueError("overlap must be smaller than max_tokens")
        self.max_tokens = max_tokens
        self.overlap = overlap
        self.counter = counter

    def split(self, text: str) -> list[str]:
        spans = [m.span() for m in _TOKEN_SPAN.finditer(text)]
        if not spans:
            return []
        if len(spans) <= self.max_tokens:
            return [text.strip()]

        step = self.max_tokens - self.overlap
        pieces = []
        for start in range(0, len(spans), step):
            window = spans[start : start + self.max_tokens]
            # Slice the original text so inner whitespace is preserved.
            piece = text[window[0][0] : window[-1][1]].strip()
            if piece:
                pieces.append(piece)
            if start + self.max_tokens >= len(spans):
                break
        return pieces
