"""In-process metrics: counters and latency observations with a JSON

snapshot and Prometheus text exposition. No agent dependency; Prometheus
scrapes the endpoint, Grafana graphs it.
"""

from __future__ import annotations

import threading
from collections import defaultdict

from app.evaluation.metrics import percentile

_MAX_OBSERVATIONS = 5000  # ring buffer per series


def _series_key(name: str, labels: dict[str, str] | None) -> tuple:
    return (name, tuple(sorted((labels or {}).items())))


class MetricsRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[tuple, float] = defaultdict(float)
        self._observations: dict[tuple, list[float]] = defaultdict(list)

    def increment(
        self, name: str, value: float = 1.0, labels: dict[str, str] | None = None
    ) -> None:
        with self._lock:
            self._counters[_series_key(name, labels)] += value

    def observe(
        self, name: str, value: float, labels: dict[str, str] | None = None
    ) -> None:
        with self._lock:
            series = self._observations[_series_key(name, labels)]
            series.append(value)
            if len(series) > _MAX_OBSERVATIONS:
                del series[: len(series) - _MAX_OBSERVATIONS]

    def snapshot(self) -> dict:
        with self._lock:
            counters = [
                {"name": name, "labels": dict(labels), "value": value}
                for (name, labels), value in sorted(self._counters.items())
            ]
            histograms = [
                {
                    "name": name,
                    "labels": dict(labels),
                    "count": len(values),
                    "p50": round(percentile(values, 50), 3),
                    "p95": round(percentile(values, 95), 3),
                    "max": round(max(values), 3) if values else 0.0,
                }
                for (name, labels), values in sorted(self._observations.items())
            ]
        return {"counters": counters, "histograms": histograms}

    def prometheus_text(self) -> str:
        lines: list[str] = []
        snapshot = self.snapshot()
        for counter in snapshot["counters"]:
            lines.append(
                f"{counter['name']}{_format_labels(counter['labels'])} {counter['value']}"
            )
        for histogram in snapshot["histograms"]:
            base = histogram["name"]
            labels = histogram["labels"]
            lines.append(f"{base}_count{_format_labels(labels)} {histogram['count']}")
            for quantile in ("p50", "p95"):
                lines.append(
                    f"{base}{_format_labels(labels | {'quantile': quantile})} "
                    f"{histogram[quantile]}"
                )
        return "\n".join(lines) + "\n"


def _format_labels(labels: dict[str, str]) -> str:
    if not labels:
        return ""
    inner = ",".join(f'{key}="{value}"' for key, value in sorted(labels.items()))
    return "{" + inner + "}"
