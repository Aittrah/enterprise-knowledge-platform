"""Token counting.

The default counter is a fast word/punctuation heuristic that tracks LLM
tokenizers closely enough for sizing chunks (English prose runs ~0.75
words per BPE token, and chunk budgets carry headroom). The counter is a
protocol so an exact tokenizer (tiktoken) can be injected at M8 when the
embedding provider fixes the real vocabulary.
"""

from __future__ import annotations

import re
from typing import Protocol

_TOKEN = re.compile(r"\w+|[^\w\s]")


class TokenCounter(Protocol):
    def count(self, text: str) -> int: ...


class HeuristicTokenCounter:
    def count(self, text: str) -> int:
        return len(_TOKEN.findall(text))


DEFAULT_COUNTER = HeuristicTokenCounter()
