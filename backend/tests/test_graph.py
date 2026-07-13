import json

import httpx
import pytest

from app.graph import (
    Entity,
    EntityExtractor,
    GraphBuilder,
    InMemoryGraphStore,
    Neo4jGraphStore,
    Relation,
    RelationDetector,
)
from app.ingestion.models import DocumentMetadata, ElementType, ExtractedDocument, ExtractedElement
from app.stores.base import StoreError

HR_TEXT = (
    "Ms. Sara Khan works in the Finance department at Acme Corp. "
    "Sara Khan reports to Bilal Ahmed. "
    "Bilal Ahmed approved $12,500.00 on 2026-05-01. "
    "Contact payroll@acme.com for questions. "
    "The Engineering department uses Kubernetes daily."
)

extractor = EntityExtractor()
detector = RelationDetector()


def entities_of(text: str) -> dict[str, str]:
    return {e.text: e.type for e in extractor.extract(text)}


# --- entity extraction ---------------------------------------------------------


def test_extracts_all_entity_types():
    found = entities_of(HR_TEXT)
    assert found["Sara Khan"] == "person"
    assert found["Bilal Ahmed"] == "person"
    assert found["Acme Corp"] == "organization"
    assert found["Finance"] == "department"
    assert found["Engineering"] == "department"
    assert found["payroll@acme.com"] == "email"
    assert found["$12,500.00"] == "money"
    assert found["2026-05-01"] == "date"


def test_repeated_mentions_are_counted_not_duplicated():
    entities = extractor.extract(HR_TEXT)
    sara = next(e for e in entities if e.text == "Sara Khan")
    assert sara.mentions == 2
    assert len([e for e in entities if e.key == sara.key]) == 1


def test_name_stoplist_blocks_common_false_positives():
    found = entities_of("The Annual Leave policy was updated in March 2026.")
    assert not any(t == "person" for t in found.values())


def test_org_words_are_not_also_person_names():
    found = entities_of("Acme Corp announced results.")
    assert found.get("Acme Corp") == "organization"
    assert "person" not in found.values()


# --- relation detection -----------------------------------------------------------


def test_typed_relations_from_verb_cues():
    entities = extractor.extract(HR_TEXT)
    relations = detector.detect(HR_TEXT, entities, source_document="hr.txt")
    types = {(r.source_key, r.type, r.target_key) for r in relations}

    assert ("person:sara khan", "WORKS_IN", "department:finance") in types
    assert ("person:sara khan", "REPORTS_TO", "person:bilal ahmed") in types
    assert ("person:bilal ahmed", "APPROVED", "money:$12,500.00") in types


def test_relations_carry_evidence_sentences():
    entities = extractor.extract(HR_TEXT)
    relations = detector.detect(HR_TEXT, entities)
    reports = next(r for r in relations if r.type == "REPORTS_TO")
    assert "reports to" in reports.evidence.lower()


def test_generic_cooccurrence_limited_to_meaningful_pairs():
    text = "Sara Khan met the Legal team about the contract."
    entities = extractor.extract(text)
    relations = detector.detect(text, entities)
    assert {r.type for r in relations} == {"CO_OCCURS"}
    # date/money pairs alone never create edges
    text2 = "Paid $500.00 on 2026-01-01."
    assert detector.detect(text2, extractor.extract(text2)) == []


# --- in-memory store ----------------------------------------------------------------


def _small_graph() -> InMemoryGraphStore:
    store = InMemoryGraphStore()
    entities = extractor.extract(HR_TEXT, source="hr.txt")
    store.upsert_entities(entities)
    store.upsert_relations(detector.detect(HR_TEXT, entities, source_document="hr.txt"))
    return store


def test_upsert_is_idempotent():
    store = _small_graph()
    before = store.stats()
    entities = extractor.extract(HR_TEXT, source="hr.txt")
    store.upsert_relations(detector.detect(HR_TEXT, entities, source_document="hr.txt"))
    assert store.stats()["relations"] == before["relations"]


def test_neighbors_expand_by_depth():
    store = _small_graph()
    depth1 = store.neighbors("person:sara khan", depth=1)
    labels1 = {e.text for e in depth1["nodes"]}
    assert {"Sara Khan", "Bilal Ahmed", "Finance"} <= labels1
    assert "$12,500.00" not in labels1  # two hops away via Bilal

    depth2 = store.neighbors("person:sara khan", depth=2)
    assert "$12,500.00" in {e.text for e in depth2["nodes"]}


def test_search_and_delete_by_source():
    store = _small_graph()
    assert store.search_nodes("khan")[0].text == "Sara Khan"
    store.delete_by_source("hr.txt")
    assert store.stats() == {"entities": 0, "relations": 0, "entities_by_type": {}}


def test_visualization_export_shape():
    viz = _small_graph().to_visualization()
    node = next(n for n in viz["nodes"] if n["label"] == "Sara Khan")
    assert node["type"] == "person" and node["degree"] >= 2
    edge = next(e for e in viz["edges"] if e["type"] == "REPORTS_TO")
    assert edge["source"] == "person:sara khan"
    assert "evidence" in edge


# --- builder ---------------------------------------------------------------------------


def _document(text: str) -> tuple[ExtractedDocument, DocumentMetadata]:
    doc = ExtractedDocument(
        source_path="hr.txt",
        file_type="txt",
        elements=[ExtractedElement(ElementType.PARAGRAPH, text)],
    )
    meta = DocumentMetadata(
        filename="hr.txt", file_type="txt", size_bytes=1, sha256="x", mime_type="text/plain",
        title="HR Notes",
    )
    return doc, meta


def test_builder_links_entities_to_document():
    store = InMemoryGraphStore()
    report = GraphBuilder(store).build(*_document(HR_TEXT))
    assert report.entities_by_type["person"] == 2
    viz = store.to_visualization()
    doc_node = next(n for n in viz["nodes"] if n["type"] == "document")
    assert doc_node["label"] == "HR Notes"
    mentioned = [e for e in viz["edges"] if e["type"] == "MENTIONED_IN"]
    assert len(mentioned) == report.entities


def test_builder_rebuild_replaces_not_duplicates():
    store = InMemoryGraphStore()
    builder = GraphBuilder(store)
    builder.build(*_document(HR_TEXT))
    first = store.stats()
    builder.build(*_document(HR_TEXT))
    assert store.stats() == first


# --- neo4j store over MockTransport --------------------------------------------------------


class Neo4jFake:
    def __init__(self):
        self.bodies: list[dict] = []
        self.auth_headers: list[str] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.bodies.append(json.loads(request.content))
        self.auth_headers.append(request.headers.get("authorization", ""))
        return httpx.Response(200, json={"results": [], "errors": []})

    def client(self) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self.handler))


def test_neo4j_upsert_entities_merges_with_label_and_auth():
    fake = Neo4jFake()
    store = Neo4jGraphStore(client=fake.client())
    store.upsert_entities([Entity(text="Sara Khan", type="person", source="hr.txt")])
    statement = fake.bodies[0]["statements"][0]
    assert statement["statement"].startswith("MERGE (e:Person {key: $key})")
    assert statement["parameters"]["name"] == "Sara Khan"
    assert fake.auth_headers[0].startswith("Basic ")


def test_neo4j_relation_cypher_and_type_whitelist():
    fake = Neo4jFake()
    store = Neo4jGraphStore(client=fake.client())
    good = Relation("person:a", "person:b", "REPORTS_TO", "a reports to b", "hr.txt")
    store.upsert_relations([good])
    assert "MERGE (a)-[r:REPORTS_TO]->(b)" in fake.bodies[0]["statements"][0]["statement"]

    with pytest.raises(StoreError, match="unknown relation type"):
        store.upsert_relations(
            [Relation("person:a", "person:b", "EVIL; DROP", "x", "hr.txt")]
        )


def test_neo4j_unknown_entity_type_rejected():
    store = Neo4jGraphStore(client=Neo4jFake().client())
    with pytest.raises(StoreError, match="unknown entity type"):
        store.upsert_entities([Entity(text="x", type="alien")])


def test_neo4j_reports_server_errors():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"results": [], "errors": [{"code": "Neo.Boom"}]})

    store = Neo4jGraphStore(client=httpx.Client(transport=httpx.MockTransport(handler)))
    with pytest.raises(StoreError, match="Neo.Boom"):
        store.stats()


def test_neo4j_unreachable_gives_actionable_error():
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    store = Neo4jGraphStore(client=httpx.Client(transport=httpx.MockTransport(refuse)))
    with pytest.raises(StoreError, match="docker compose"):
        store.stats()


# --- live integration (auto-skip while Neo4j is down) ------------------------------------------


def _neo4j_up() -> bool:
    try:
        return httpx.get("http://localhost:7474", timeout=1.0).status_code < 500
    except httpx.HTTPError:
        return False


@pytest.mark.skipif(not _neo4j_up(), reason="neo4j not running (docker compose up)")
def test_neo4j_live_roundtrip():
    store = Neo4jGraphStore()
    store.delete_by_source("it-test.txt")
    store.upsert_entities([Entity(text="Test Person", type="person", source="it-test.txt")])
    assert any("test person" in n["key"] for n in store.search_nodes("Test Person"))
    store.delete_by_source("it-test.txt")
