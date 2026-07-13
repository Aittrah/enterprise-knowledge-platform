"""OpenAI embeddings adapter (text-embedding-3-*)."""

from __future__ import annotations

import httpx

from app.embeddings.base import InputType, Vector
from app.embeddings.providers.http import post_json, require_api_key

_DIMENSIONS = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
}


class OpenAIProvider:
    name = "openai"

    def __init__(
        self,
        model: str = "text-embedding-3-small",
        api_key: str | None = None,
        base_url: str = "https://api.openai.com/v1",
        client: httpx.Client | None = None,
    ) -> None:
        self.model = model
        self.dimension = _DIMENSIONS.get(model, 1536)
        self._api_key = require_api_key("OPENAI_API_KEY", api_key)
        self._url = f"{base_url}/embeddings"
        self._client = client or httpx.Client()

    def embed(self, texts: list[str], input_type: InputType = "document") -> list[Vector]:
        # OpenAI models are symmetric: no query/document distinction.
        data = post_json(
            self._client,
            self._url,
            headers={"Authorization": f"Bearer {self._api_key}"},
            payload={"model": self.model, "input": texts},
        )
        rows = sorted(data["data"], key=lambda r: r["index"])
        return [row["embedding"] for row in rows]
