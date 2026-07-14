import json
import logging
from pathlib import Path

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.core.config import Settings
from app.observability import MetricsRegistry, Tracer, estimate_cost
from app.observability.logs import JsonFormatter, log_event


# --- metrics registry -----------------------------------------------------------


def test_counters_accumulate_per_label_set():
    registry = MetricsRegistry()
    registry.increment("requests", labels={"path": "/a"})
    registry.increment("requests", labels={"path": "/a"})
    registry.increment("requests", labels={"path": "/b"})
    counters = {tuple(c["labels"].items()): c["value"] for c in registry.snapshot()["counters"]}
    assert counters[(("path", "/a"),)] == 2
    assert counters[(("path", "/b"),)] == 1


def test_histograms_report_percentiles():
    registry = MetricsRegistry()
    for value in range(1, 101):
        registry.observe("latency_ms", float(value))
    histogram = registry.snapshot()["histograms"][0]
    assert histogram["count"] == 100
    assert histogram["p50"] == 50
    assert histogram["p95"] == 95
    assert histogram["max"] == 100


def test_prometheus_text_format():
    registry = MetricsRegistry()
    registry.increment("ekip_queries_total", labels={"agent": "hr"})
    registry.observe("ekip_retrieval_ms", 12.5)
    text = registry.prometheus_text()
    assert 'ekip_queries_total{agent="hr"} 1.0' in text
    assert "ekip_retrieval_ms_count 1" in text
    assert 'quantile="p95"' in text


# --- cost ------------------------------------------------------------------------------


def test_cost_estimation_known_and_unknown_models():
    known = estimate_cost("gpt-4o-mini", 1_000_000, 1_000_000)
    assert known["usd"] == 0.75  # 0.15 in + 0.60 out
    assert not known["estimated"]

    free = estimate_cost("extractive", 5000, 5000)
    assert free["usd"] == 0.0

    unknown = estimate_cost("mystery-model", 1_000_000, 0)
    assert unknown["estimated"] and unknown["usd"] > 0


# --- tracing -----------------------------------------------------------------------------


def test_tracer_records_nested_spans():
    tracer = Tracer()
    with tracer.span("ask"):
        with tracer.span("retrieve"):
            pass
        with tracer.span("llm"):
            pass
    names = {span["name"]: span for span in tracer.spans}
    assert names["retrieve"]["parent"] == "ask"
    assert names["llm"]["parent"] == "ask"
    assert names["ask"]["parent"] is None
    assert tracer.total_ms() >= names["retrieve"]["ms"]


# --- logging ---------------------------------------------------------------------------------


def test_json_formatter_emits_parseable_lines():
    record = logging.LogRecord("ekip", logging.INFO, __file__, 1, "indexed %s", ("doc",), None)
    record.extra_fields = {"source": "leave.txt", "chunks": 3}
    line = JsonFormatter().format(record)
    payload = json.loads(line)
    assert payload["message"] == "indexed doc"
    assert payload["source"] == "leave.txt"
    assert payload["level"] == "INFO"


def test_log_event_helper():
    logger = logging.getLogger("ekip-test")
    log_event(logger, "hello", user="u1")  # must not raise


# --- API integration ----------------------------------------------------------------------------


def test_request_metrics_and_monitoring_endpoints(tmp_path: Path):
    app = create_app(
        Settings(data_dir=tmp_path / "data", jwt_secret="test-secret-" + "x" * 24)
    )
    client = TestClient(app)
    token = client.post(
        "/api/auth/register",
        json={"email": "a@b.co", "password": "longenough", "name": "A"},
    ).json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"

    client.post("/api/chat", json={"question": "any documents about leave?"})

    snapshot = client.get("/api/monitoring/metrics").json()
    counter_names = {c["name"] for c in snapshot["counters"]}
    assert "ekip_http_requests_total" in counter_names
    assert "ekip_queries_total" in counter_names
    histogram_names = {h["name"] for h in snapshot["histograms"]}
    assert "ekip_http_request_ms" in histogram_names
    assert "ekip_retrieval_ms" in histogram_names

    prometheus = client.get("/api/monitoring/prometheus")
    assert prometheus.status_code == 200
    assert "ekip_http_requests_total" in prometheus.text

    summary = client.get("/api/analytics/summary").json()
    assert "cost_usd" in summary
