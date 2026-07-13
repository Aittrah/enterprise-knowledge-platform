import json
from pathlib import Path

import httpx
import pytest

from app.embeddings import EmbeddingService, create_provider
from app.stores import (
    InMemoryVectorStore,
    KnowledgeBaseIndexer,
    QdrantVectorStore,
    StoreError,
    VectorRecord,
)
from app.stores.memory import matches
from app.stores.pgvector import build_where, vector_literal
from app.stores.qdrant import to_point_id, to_qdrant_filter


def rec(rid: str, vector: list[float], text: str = "", **metadata) -> VectorRecord:
    return VectorRecord(id=rid, vector=vector, text=text or rid, metadata=metadata)


# --- in-memory store (reference implementation) --------------------------------


def test_memory_search_ranks_by_cosine_and_respects_top_k():
    store = InMemoryVectorStore()
    store.upsert(
        [
            rec("a", [1.0, 0.0]),
            rec("b", [0.9, 0.1]),
            rec("c", [0.0, 1.0]),
        ]
    )
    hits = store.search([1.0, 0.0], top_k=2)
    assert [h.id for h in hits] == ["a", "b"]
    assert hits[0].score == pytest.approx(1.0)


def test_memory_filters_equality_and_membership():
    store = InMemoryVectorStore()
    store.upsert(
        [
            rec("a", [1.0, 0.0], source="x.pdf", file_type="pdf"),
            rec("b", [1.0, 0.0], source="y.docx", file_type="docx"),
        ]
    )
    assert [h.id for h in store.search([1.0, 0.0], filters={"source": "x.pdf"})] == ["a"]
    assert [
        h.id for h in store.search([1.0, 0.0], filters={"file_type": ["docx", "html"]})
    ] == ["b"]


def test_memory_upsert_overwrites_and_delete_by_filter():
    store = InMemoryVectorStore()
    store.upsert([rec("a", [1.0], source="x")])
    store.upsert([rec("a", [0.5], source="x")])  # same id: overwrite
    assert store.count() == 1
    store.delete_by_filter({"source": "x"})
    assert store.count() == 0


def test_matches_helper():
    assert matches({"k": "v"}, None)
    assert matches({"k": "v"}, {"k": "v"})
    assert not matches({"k": "v"}, {"k": "other"})
    assert matches({"k": "v"}, {"k": ["v", "w"]})
    assert not matches({}, {"k": "v"})


# --- qdrant translation helpers --------------------------------------------------


def test_qdrant_filter_translation():
    assert to_qdrant_filter(None) is None
    assert to_qdrant_filter({"source": "a.pdf", "type": ["pdf", "docx"]}) == {
        "must": [
            {"key": "source", "match": {"value": "a.pdf"}},
            {"key": "type", "match": {"any": ["pdf", "docx"]}},
        ]
    }


def test_chunk_ids_map_to_valid_qdrant_uuids():
    chunk_id = "a" * 32
    assert to_point_id(chunk_id) == "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"


# --- qdrant store over MockTransport ----------------------------------------------


class QdrantFake:
    """Minimal fake of the Qdrant REST surface, recording every request."""

    def __init__(self, exists: bool = False):
        self.exists = exists
        self.requests: list[tuple[str, str, dict | None]] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content) if request.content else None
        path = request.url.path
        self.requests.append((request.method, path, body))
        if request.method == "GET" and path.endswith("/collections/ekip_chunks"):
            return httpx.Response(200 if self.exists else 404, json={})
        if path.endswith("/points/search"):
            return httpx.Response(
                200,
                json={
                    "result": [
                        {
                            "id": "uuid-ignored",
                            "score": 0.87,
                            "payload": {
                                "chunk_id": "c" * 32,
                                "text": "leave policy text",
                                "source": "policy.pdf",
                            },
                        }
                    ]
                },
            )
        if path.endswith("/points/count"):
            return httpx.Response(200, json={"result": {"count": 7}})
        return httpx.Response(200, json={"result": {}})

    def client(self) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self.handler))


def test_qdrant_ensure_ready_creates_missing_collection():
    fake = QdrantFake(exists=False)
    QdrantVectorStore(client=fake.client()).ensure_ready(384)
    put = [r for r in fake.requests if r[0] == "PUT"]
    assert put[0][2] == {"vectors": {"size": 384, "distance": "Cosine"}}


def test_qdrant_ensure_ready_skips_existing_collection():
    fake = QdrantFake(exists=True)
    QdrantVectorStore(client=fake.client()).ensure_ready(384)
    assert not [r for r in fake.requests if r[0] == "PUT"]


def test_qdrant_upsert_builds_points_with_uuid_and_payload():
    fake = QdrantFake()
    store = QdrantVectorStore(client=fake.client())
    store.upsert([rec("b" * 32, [0.1, 0.2], text="hello", source="a.pdf")])
    method, path, body = fake.requests[-1]
    assert (method, path) == ("PUT", "/collections/ekip_chunks/points")
    point = body["points"][0]
    assert point["id"] == "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
    assert point["payload"] == {"chunk_id": "b" * 32, "text": "hello", "source": "a.pdf"}


def test_qdrant_search_sends_filter_and_parses_hits():
    fake = QdrantFake()
    store = QdrantVectorStore(client=fake.client())
    hits = store.search([0.1, 0.2], top_k=5, filters={"source": "policy.pdf"})
    _, _, body = fake.requests[-1]
    assert body["limit"] == 5
    assert body["filter"]["must"][0]["key"] == "source"
    assert hits[0].id == "c" * 32
    assert hits[0].score == pytest.approx(0.87)
    assert hits[0].text == "leave policy text"
    assert hits[0].metadata == {"source": "policy.pdf"}  # text/chunk_id split out


def test_qdrant_count_and_delete():
    fake = QdrantFake()
    store = QdrantVectorStore(client=fake.client())
    assert store.count() == 7
    store.delete_by_filter({"source": "a.pdf"})
    method, path, body = fake.requests[-1]
    assert path.endswith("/points/delete")
    assert body["filter"]["must"][0]["match"]["value"] == "a.pdf"


def test_qdrant_unreachable_gives_actionable_error():
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    store = QdrantVectorStore(client=httpx.Client(transport=httpx.MockTransport(refuse)))
    with pytest.raises(StoreError, match="docker compose"):
        store.count()


# --- pgvector SQL builders ----------------------------------------------------------


def test_pgvector_vector_literal():
    assert vector_literal([0.1, -2.0, 3.25]) == "[0.1,-2.0,3.25]"


def test_pgvector_where_builder():
    where, params = build_where({"source": "a.pdf", "type": ["pdf", "docx"]})
    assert where == " WHERE metadata->>%s = %s AND metadata->>%s = ANY(%s)"
    assert params == ["source", "a.pdf", "type", ["pdf", "docx"]]
    assert build_where(None) == ("", [])


# --- indexer (write path, offline stack) ----------------------------------------------


@pytest.fixture
def indexer_env(tmp_path: Path):
    store = InMemoryVectorStore()
    service = EmbeddingService(create_provider("hashing"))
    return store, KnowledgeBaseIndexer(store, service)


def _ingest(tmp_path: Path, name: str, text: str):
    from app.ingestion import IngestionPipeline

    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    result = IngestionPipeline(tmp_path / "v.json").ingest(path)
    return result.document, result.metadata


def test_indexer_indexes_document_chunks(indexer_env, tmp_path: Path):
    store, indexer = indexer_env
    document, metadata = _ingest(
        tmp_path, "policy.txt", "Employees accrue 22 days of annual leave every year."
    )
    report = indexer.index(document, metadata)
    assert report.chunks_indexed == store.count() > 0
    assert not report.superseded_previous
    hit = store.search([0.0] * 384, top_k=1)[0]
    assert hit.metadata["source"] == "policy.txt"
    assert hit.metadata["version"] == 1


def test_indexer_supersedes_previous_version(indexer_env, tmp_path: Path):
    store, indexer = indexer_env
    doc1, meta1 = _ingest(tmp_path, "policy.txt", "Old policy: 20 days of leave.")
    indexer.index(doc1, meta1)

    (tmp_path / "policy.txt").write_text("New policy: 25 days of leave.", encoding="utf-8")
    doc2, meta2 = _ingest(tmp_path, "policy.txt", "New policy: 25 days of leave.")
    report = indexer.index(doc2, meta2)

    assert report.superseded_previous
    texts = [store.search([0.0] * 384, top_k=10)[i].text for i in range(store.count())]
    assert all("New policy" in t or "Old" not in t for t in texts)
    assert store.count() == report.chunks_indexed  # no stale chunks


def test_indexer_refuses_invalid_chunk_sets(indexer_env, tmp_path: Path):
    from app.processing.chunking import ChunkGenerator, ChunkValidator

    store, _ = indexer_env
    service = EmbeddingService(create_provider("hashing"))
    strict = KnowledgeBaseIndexer(
        store,
        service,
        generator=ChunkGenerator(strategy="token", max_tokens=512),
        validator=ChunkValidator(max_tokens=2, size_tolerance=1.0),  # impossible limit
    )
    document, metadata = _ingest(tmp_path, "big.txt", "word " * 200)
    with pytest.raises(StoreError, match="refusing to index"):
        strict.index(document, metadata)
    assert store.count() == 0  # nothing partially written


def test_semantic_search_end_to_end_offline(indexer_env, tmp_path: Path):
    store, indexer = indexer_env
    service = EmbeddingService(create_provider("hashing"))
    hr_doc, hr_meta = _ingest(
        tmp_path, "leave.txt", "Employees accrue annual leave days monthly under the leave policy."
    )
    ops_doc, ops_meta = _ingest(
        tmp_path, "k8s.txt", "Kubernetes cluster autoscaling requires resource limits on pods."
    )
    indexer.index(hr_doc, hr_meta)
    indexer.index(ops_doc, ops_meta)

    query = service.embed_query("how many annual leave days do employees get")
    hits = store.search(query, top_k=2)
    assert hits[0].metadata["source"] == "leave.txt"

    filtered = store.search(query, top_k=2, filters={"source": "k8s.txt"})
    assert all(h.metadata["source"] == "k8s.txt" for h in filtered)


# --- live integration (auto-skip while services are down) ------------------------------


def _qdrant_up() -> bool:
    try:
        return httpx.get("http://localhost:6333/collections", timeout=1.0).status_code == 200
    except httpx.HTTPError:
        return False


@pytest.mark.skipif(not _qdrant_up(), reason="qdrant not running (docker compose up)")
def test_qdrant_live_roundtrip():
    store = QdrantVectorStore(collection="ekip_test_roundtrip")
    store.ensure_ready(8)
    store.delete_by_filter({"source": "it.txt"})
    store.upsert([rec("d" * 32, [1.0, 0, 0, 0, 0, 0, 0, 0], text="hello", source="it.txt")])
    hits = store.search([1.0, 0, 0, 0, 0, 0, 0, 0], top_k=1)
    assert hits[0].text == "hello"
    store.delete_by_filter({"source": "it.txt"})
