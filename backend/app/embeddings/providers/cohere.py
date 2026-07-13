"""Cohere embeddings adapter (embed v2 API)."""

from __future__ import annotations

import httpx

from app.embeddings.base import InputType, Vector
from app.embeddings.providers.http import post_json, require_api_key

_INPUT_TYPES = {"document": "search_document", "query": "search_query"}


class CohereProvider:
    name = "cohere"

    def __init__(
        self,
        model: str = "embed-english-v3.0",
        api_key: str | None = None,
        base_url: str = "https://api.cohere.com/v2",
        client: httpx.Client | None = None,
    ) -> None:
        self.model = model
        self.dimension = 1024
        self._api_key = require_api_key("COHERE_API_KEY", api_key)
        self._url = f"{base_url}/embed"
        self._client = client or httpx.Client()

    def embed(self, texts: list[str], input_type: InputType = "document") -> list[Vector]:
        data = post_json(
            self._client,
            self._url,
            headers={"Authorization": f"Bearer {self._api_key}"},
            payload={
                "model": self.model,
                "texts": texts,
                "input_type": _INPUT_TYPES[input_type],
                "embedding_types": ["float"],
            },
        )
        return data["embeddings"]["float"]
