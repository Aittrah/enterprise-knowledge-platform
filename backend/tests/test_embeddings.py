import json
import math
from pathlib import Path

import httpx
import pytest

from app.embeddings import (
    EmbeddingCache,
    EmbeddingService,
    ProviderConfigurationError,
    ProviderRequestError,
    create_provider,
)
from app.embeddings.cache import cache_key
from app.embeddings.providers import CohereProvider, HashingProvider, OpenAIProvider, VoyageProvider
from app.embeddings.providers.local import format_for_model


# --- REST adapters (httpx.MockTransport — no network, no keys) ----------------


def _mock_client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_openai_adapter_payload_and_parsing():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers["authorization"]
        seen["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "data": [  # deliberately out of order: adapter must sort by index
                    {"index": 1, "embedding": [0.3, 0.4]},
                    {"index": 0, "embedding": [0.1, 0.2]},
                ]
            },
        )

    provider = OpenAIProvider(api_key="sk-test", client=_mock_client(handler))
    vectors = provider.embed(["alpha", "beta"])
    assert vectors == [[0.1, 0.2], [0.3, 0.4]]
    assert seen["auth"] == "Bearer sk-test"
    assert seen["payload"] == {"model": "text-embedding-3-small", "input": ["alpha", "beta"]}


def test_cohere_adapter_maps_input_types():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["payload"] = json.loads(request.content)
        return httpx.Response(200, json={"embeddings": {"float": [[1.0, 2.0]]}})

    provider = CohereProvider(api_key="co-test", client=_mock_client(handler))
    provider.embed(["q"], input_type="query")
    assert seen["payload"]["input_type"] == "search_query"
    provider.embed(["d"], input_type="document")
    assert seen["payload"]["input_type"] == "search_document"


def test_voyage_adapter_passes_input_type_through():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["payload"] = json.loads(request.content)
        return httpx.Response(200, json={"data": [{"index": 0, "embedding": [0.5]}]})

    provider = VoyageProvider(api_key="vo-test", client=_mock_client(handler))
    assert provider.embed(["x"], input_type="query") == [[0.5]]
    assert seen["payload"]["input_type"] == "query"


def test_http_error_becomes_retryable_provider_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, text="rate limited")

    provider = OpenAIProvider(api_key="sk-test", client=_mock_client(handler))
    with pytest.raises(ProviderRequestError, match="429"):
        provider.embed(["x"])


def test_missing_api_key_is_a_configuration_error(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ProviderConfigurationError, match="OPENAI_API_KEY"):
        OpenAIProvider()


def test_registry_creates_and_rejects():
    assert create_provider("hashing").name == "hashing"
    with pytest.raises(ProviderConfigurationError, match="Unknown"):
        create_provider("quantum")


# --- local model prefix conventions (pure function, no torch) ------------------


def test_e5_prefixes_queries_and_passages():
    assert format_for_model(["hi"], "intfloat/e5-small-v2", "query") == ["query: hi"]
    assert format_for_model(["hi"], "intfloat/e5-small-v2", "document") == ["passage: hi"]


def test_bge_prefixes_only_queries():
    out_q = format_for_model(["hi"], "BAAI/bge-small-en-v1.5", "query")
    assert out_q[0].startswith("Represent this sentence")
    assert format_for_model(["hi"], "BAAI/bge-small-en-v1.5", "document") == ["hi"]


# --- hashing provider ----------------------------------------------------------


def _cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def test_hashing_provider_is_deterministic_and_normalized():
    provider = HashingProvider(dimension=128)
    v1, v2 = provider.embed(["annual leave policy"] * 2)
    assert v1 == v2
    assert math.isclose(sum(x * x for x in v1), 1.0, rel_tol=1e-6)
    assert len(v1) == 128


def test_hashing_provider_ranks_related_text_closer():
    provider = HashingProvider()
    doc, related, unrelated = provider.embed(
        [
            "employees accrue annual leave days each month",
            "annual leave days accrue monthly for employees",
            "kubernetes cluster autoscaling configuration guide",
        ]
    )
    assert _cosine(doc, related) > _cosine(doc, unrelated) + 0.3


# --- cache ----------------------------------------------------------------------


def test_cache_roundtrip_float32(tmp_path: Path):
    cache = EmbeddingCache(tmp_path / "emb.db")
    key = cache_key("p", "m", "document", "text")
    cache.set_many({key: [0.125, -2.5, 3.0]})
    assert cache.get_many([key]) == {key: [0.125, -2.5, 3.0]}
    assert len(cache) == 1


def test_cache_keys_separate_models_and_input_types():
    base = ("openai", "text-embedding-3-small", "document", "same text")
    assert cache_key(*base) != cache_key("openai", "other-model", "document", "same text")
    assert cache_key(*base) != cache_key("openai", "text-embedding-3-small", "query", "same text")


# --- service ---------------------------------------------------------------------


class CountingProvider:
    name = "counting"
    model = "v1"
    dimension = 4

    def __init__(self, fail_times: int = 0):
        self.batches: list[list[str]] = []
        self._fail_times = fail_times

    def embed(self, texts, input_type="document"):
        if self._fail_times > 0:
            self._fail_times -= 1
            raise ProviderRequestError("transient")
        self.batches.append(list(texts))
        return [[float(len(t)), 0.0, 0.0, 0.0] for t in texts]


def test_service_uses_cache_on_second_call(tmp_path: Path):
    provider = CountingProvider()
    service = EmbeddingService(provider, cache_path=tmp_path / "emb.db")
    first = service.embed_texts(["a", "bb", "ccc"])
    second = service.embed_texts(["a", "bb", "ccc"])
    assert first == second
    assert len(provider.batches) == 1  # second call fully served from cache
    assert service.stats["cache_hits"] == 3


def test_service_embeds_only_cache_misses(tmp_path: Path):
    provider = CountingProvider()
    service = EmbeddingService(provider, cache_path=tmp_path / "emb.db")
    service.embed_texts(["a", "bb"])
    service.embed_texts(["a", "bb", "ccc"])
    assert provider.batches == [["a", "bb"], ["ccc"]]


def test_service_deduplicates_within_a_call():
    provider = CountingProvider()
    service = EmbeddingService(provider)
    vectors = service.embed_texts(["dup", "dup", "other"])
    assert provider.batches == [["dup", "other"]]
    assert vectors[0] == vectors[1]


def test_service_batches_large_inputs():
    provider = CountingProvider()
    service = EmbeddingService(provider, batch_size=10)
    service.embed_texts([f"text {i}" for i in range(25)])
    assert [len(b) for b in provider.batches] == [10, 10, 5]


def test_service_retries_transient_failures(monkeypatch):
    monkeypatch.setattr("app.embeddings.service.time.sleep", lambda s: None)
    provider = CountingProvider(fail_times=2)
    service = EmbeddingService(provider, max_retries=3)
    assert service.embed_texts(["x"]) == [[1.0, 0.0, 0.0, 0.0]]


def test_service_raises_after_retry_budget(monkeypatch):
    monkeypatch.setattr("app.embeddings.service.time.sleep", lambda s: None)
    provider = CountingProvider(fail_times=5)
    service = EmbeddingService(provider, max_retries=3)
    with pytest.raises(ProviderRequestError):
        service.embed_texts(["x"])


def test_query_and_document_cached_separately(tmp_path: Path):
    provider = CountingProvider()
    service = EmbeddingService(provider, cache_path=tmp_path / "emb.db")
    service.embed_texts(["same"], input_type="document")
    service.embed_query("same")
    assert len(provider.batches) == 2  # query is not served by the document cache


# --- end-to-end with chunking ------------------------------------------------------


def test_chunks_to_vectors(tmp_path: Path, sample_docx: Path):
    from app.ingestion import IngestionPipeline
    from app.processing.chunking import ChunkGenerator

    result = IngestionPipeline(tmp_path / "v.json").ingest(sample_docx)
    chunks = ChunkGenerator().generate(result.document, result.metadata)
    service = EmbeddingService(create_provider("hashing"), cache_path=tmp_path / "emb.db")
    vectors = service.embed_texts([c.text for c in chunks])
    assert len(vectors) == len(chunks)
    assert all(len(v) == 384 for v in vectors)
