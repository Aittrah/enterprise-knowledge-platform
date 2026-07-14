"""Minimal span tracing for the RAG pipeline.

    tracer = Tracer()
    with tracer.span("retrieve"):
        with tracer.span("embed_query"):
            ...
    tracer.spans  # [{"name", "parent", "ms"}, ...]

OpenTelemetry replaces this at deployment; the span names are the contract.
"""

from __future__ import annotations

import time
from contextlib import contextmanager


class Tracer:
    def __init__(self) -> None:
        self.spans: list[dict] = []
        self._stack: list[str] = []

    @contextmanager
    def span(self, name: str):
        parent = self._stack[-1] if self._stack else None
        self._stack.append(name)
        started = time.perf_counter()
        try:
            yield
        finally:
            self._stack.pop()
            self.spans.append(
                {
                    "name": name,
                    "parent": parent,
                    "ms": round((time.perf_counter() - started) * 1000, 3),
                }
            )

    def total_ms(self) -> float:
        return round(sum(s["ms"] for s in self.spans if s["parent"] is None), 3)
