"""Qdrant vector store over its REST API (httpx — consistent with the

embedding adapters, MockTransport-testable, no qdrant-client dependency).
"""

from __future__ import annotations

import uuid

import httpx

from app.stores.base import Filters, SearchHit, StoreError, VectorRecord


def to_qdrant_filter(filters: Filters | None) -> dict | None:
    """{"source": "a.pdf", "type": ["pdf","docx"]} -> Qdrant must-clauses."""
    if not filters:
        return None
    must = []
    for key, expected in filters.items():
        if isinstance(expected, (list, tuple, set)):
            must.append({"key": key, "match": {"any": list(expected)}})
        else:
            must.append({"key": key, "match": {"value": expected}})
    return {"must": must}


def to_point_id(chunk_id: str) -> str:
    """Qdrant point ids must be UUIDs or unsigned ints; chunk ids are
    32-hex blake2b digests, which map 1:1 onto UUID format."""
    return str(uuid.UUID(hex=chunk_id))


class QdrantVectorStore:
    def __init__(
        self,
        collection: str = "ekip_chunks",
        base_url: str = "http://localhost:6333",
        client: httpx.Client | None = None,
    ) -> None:
        self.collection = collection
        self._base = base_url.rstrip("/")
        self._client = client or httpx.Client(timeout=30.0)

    # -- plumbing -------------------------------------------------------------

    def _request(self, method: str, path: str, json: dict | None = None) -> dict:
        try:
            response = self._client.request(method, f"{self._base}{path}", json=json)
        except httpx.HTTPError as exc:
            raise StoreError(
                f"Qdrant unreachable at {self._base} — is `docker compose up` running? ({exc})"
            ) from exc
        if response.status_code >= 400:
            raise StoreError(
                f"Qdrant {method} {path} -> {response.status_code}: {response.text[:300]}"
            )
        return response.json()

    # -- VectorStore ------------------------------------------------------------

    def ensure_ready(self, dimension: int) -> None:
        try:
            self._request("GET", f"/collections/{self.collection}")
            return
        except StoreError:
            pass
        self._request(
            "PUT",
            f"/collections/{self.collection}",
            json={"vectors": {"size": dimension, "distance": "Cosine"}},
        )

    def upsert(self, records: list[VectorRecord]) -> None:
        if not records:
            return
        points = [
            {
                "id": to_point_id(r.id),
                "vector": r.vector,
                "payload": {"chunk_id": r.id, "text": r.text, **r.metadata},
            }
            for r in records
        ]
        self._request(
            "PUT", f"/collections/{self.collection}/points?wait=true", json={"points": points}
        )

    def search(
        self, vector: list[float], top_k: int = 10, filters: Filters | None = None
    ) -> list[SearchHit]:
        body: dict = {"vector": vector, "limit": top_k, "with_payload": True}
        qfilter = to_qdrant_filter(filters)
        if qfilter:
            body["filter"] = qfilter
        data = self._request(
            "POST", f"/collections/{self.collection}/points/search", json=body
        )
        hits = []
        for row in data.get("result", []):
            payload = dict(row.get("payload") or {})
            chunk_id = payload.pop("chunk_id", str(row["id"]))
            text = payload.pop("text", "")
            hits.append(SearchHit(chunk_id, float(row["score"]), text, payload))
        return hits

    def delete_by_filter(self, filters: Filters) -> None:
        qfilter = to_qdrant_filter(filters)
        if not qfilter:
            return
        self._request(
            "POST",
            f"/collections/{self.collection}/points/delete?wait=true",
            json={"filter": qfilter},
        )

    def count(self) -> int:
        data = self._request(
            "POST", f"/collections/{self.collection}/points/count", json={"exact": True}
        )
        return int(data["result"]["count"])
