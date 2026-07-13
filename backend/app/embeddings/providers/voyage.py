"""Voyage AI embeddings adapter."""

from __future__ import annotations

import httpx

from app.embeddings.base import InputType, Vector
from app.embeddings.providers.http import post_json, require_api_key

_DIMENSIONS = {"voyage-3": 1024, "voyage-3-lite": 512, "voyage-code-3": 1024}


class VoyageProvider:
    name = "voyage"

    def __init__(
        self,
        model: str = "voyage-3",
        api_key: str | None = None,
        base_url: str = "https://api.voyageai.com/v1",
        client: httpx.Client | None = None,
    ) -> None:
        self.model = model
        self.dimension = _DIMENSIONS.get(model, 1024)
        self._api_key = require_api_key("VOYAGE_API_KEY", api_key)
        self._url = f"{base_url}/embeddings"
        self._client = client or httpx.Client()

    def embed(self, texts: list[str], input_type: InputType = "document") -> list[Vector]:
        data = post_json(
            self._client,
            self._url,
            headers={"Authorization": f"Bearer {self._api_key}"},
            payload={"model": self.model, "input": texts, "input_type": input_type},
        )
        rows = sorted(data["data"], key=lambda r: r["index"])
        return [row["embedding"] for row in rows]
