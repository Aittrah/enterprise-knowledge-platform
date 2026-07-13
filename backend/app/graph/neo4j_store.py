"""Neo4j graph store over the HTTP transaction API (httpx, basic auth —

consistent with the Qdrant and embedding adapters, MockTransport-testable,
no driver dependency).

Node labels and relationship types are interpolated into Cypher (Neo4j
does not parameterize them), so both are validated against whitelists.
"""

from __future__ import annotations

import httpx

from app.graph.entities import Entity
from app.graph.relations import Relation
from app.stores.base import StoreError

_NODE_LABELS = {
    "person": "Person",
    "organization": "Organization",
    "department": "Department",
    "email": "Email",
    "money": "Money",
    "date": "Date",
    "document": "Document",
}
_RELATION_TYPES = frozenset(
    {"REPORTS_TO", "WORKS_IN", "EMPLOYED_BY", "MANAGES", "APPROVED", "CO_OCCURS", "MENTIONED_IN"}
)


class Neo4jGraphStore:
    def __init__(
        self,
        base_url: str = "http://localhost:7474",
        database: str = "neo4j",
        auth: tuple[str, str] = ("neo4j", "ekip_dev_password"),
        client: httpx.Client | None = None,
    ) -> None:
        self._url = f"{base_url.rstrip('/')}/db/{database}/tx/commit"
        self._auth = auth
        self._client = client or httpx.Client(timeout=30.0)

    def _run(self, statements: list[dict]) -> list[dict]:
        try:
            response = self._client.post(
                self._url, json={"statements": statements}, auth=self._auth
            )
        except httpx.HTTPError as exc:
            raise StoreError(
                f"Neo4j unreachable at {self._url} — is `docker compose up` running? ({exc})"
            ) from exc
        if response.status_code >= 400:
            raise StoreError(f"Neo4j returned {response.status_code}: {response.text[:300]}")
        data = response.json()
        if data.get("errors"):
            raise StoreError(f"Neo4j errors: {data['errors'][:3]}")
        return data.get("results", [])

    @staticmethod
    def _label(entity_type: str) -> str:
        try:
            return _NODE_LABELS[entity_type]
        except KeyError:
            raise StoreError(f"unknown entity type '{entity_type}'") from None

    def upsert_entities(self, entities: list[Entity]) -> None:
        if not entities:
            return
        statements = [
            {
                "statement": (
                    f"MERGE (e:{self._label(entity.type)} {{key: $key}}) "
                    "ON CREATE SET e.name = $name, e.mentions = $mentions, e.source = $source "
                    "ON MATCH SET e.mentions = e.mentions + $mentions"
                ),
                "parameters": {
                    "key": entity.key,
                    "name": entity.text,
                    "mentions": entity.mentions,
                    "source": entity.source,
                },
            }
            for entity in entities
        ]
        self._run(statements)

    def upsert_relations(self, relations: list[Relation]) -> None:
        if not relations:
            return
        statements = []
        for relation in relations:
            if relation.type not in _RELATION_TYPES:
                raise StoreError(f"unknown relation type '{relation.type}'")
            statements.append(
                {
                    "statement": (
                        "MATCH (a {key: $source_key}), (b {key: $target_key}) "
                        f"MERGE (a)-[r:{relation.type}]->(b) "
                        "ON CREATE SET r.evidence = $evidence, r.document = $document"
                    ),
                    "parameters": {
                        "source_key": relation.source_key,
                        "target_key": relation.target_key,
                        "evidence": relation.evidence,
                        "document": relation.source_document,
                    },
                }
            )
        self._run(statements)

    def delete_by_source(self, source: str) -> None:
        self._run(
            [
                {
                    "statement": "MATCH ()-[r {document: $source}]-() DELETE r",
                    "parameters": {"source": source},
                },
                {
                    "statement": "MATCH (e {source: $source}) DETACH DELETE e",
                    "parameters": {"source": source},
                },
            ]
        )

    def search_nodes(self, term: str) -> list[dict]:
        results = self._run(
            [
                {
                    "statement": (
                        "MATCH (e) WHERE toLower(e.name) CONTAINS toLower($term) "
                        "RETURN e.key AS key, e.name AS name, labels(e) AS labels "
                        "LIMIT 25"
                    ),
                    "parameters": {"term": term},
                }
            ]
        )
        rows = results[0]["data"] if results else []
        return [
            {"key": row["row"][0], "name": row["row"][1], "labels": row["row"][2]}
            for row in rows
        ]

    def stats(self) -> dict:
        results = self._run(
            [
                {"statement": "MATCH (e) RETURN count(e)"},
                {"statement": "MATCH ()-[r]->() RETURN count(r)"},
            ]
        )
        entities = results[0]["data"][0]["row"][0] if results else 0
        relations = results[1]["data"][0]["row"][0] if len(results) > 1 else 0
        return {"entities": entities, "relations": relations}
