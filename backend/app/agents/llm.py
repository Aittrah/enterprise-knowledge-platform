"""LLM client contract + an OpenAI-compatible REST adapter.

The /chat/completions wire format is the industry lingua franca — the same
adapter reaches OpenAI, Azure OpenAI, Groq, Together, or a local Ollama by
changing ``base_url``. Anthropic gets its own adapter when needed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

import httpx

from app.embeddings.providers.http import post_json, require_api_key

Message = dict[str, str]  # {"role": ..., "content": ...}


@dataclass
class LLMReply:
    text: str
    model: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    raw: dict = field(default_factory=dict)


@runtime_checkable
class LLMClient(Protocol):
    name: str

    def chat(self, messages: list[Message], temperature: float = 0.2) -> LLMReply: ...


class OpenAICompatibleClient:
    name = "openai-compatible"

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key: str | None = None,
        api_key_env: str = "OPENAI_API_KEY",
        base_url: str = "https://api.openai.com/v1",
        client: httpx.Client | None = None,
    ) -> None:
        self.model = model
        self._api_key = require_api_key(api_key_env, api_key)
        self._url = f"{base_url.rstrip('/')}/chat/completions"
        self._client = client or httpx.Client(timeout=120.0)

    def chat(self, messages: list[Message], temperature: float = 0.2) -> LLMReply:
        data = post_json(
            self._client,
            self._url,
            headers={"Authorization": f"Bearer {self._api_key}"},
            payload={
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
            },
        )
        usage = data.get("usage", {})
        return LLMReply(
            text=data["choices"][0]["message"]["content"],
            model=data.get("model", self.model),
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            raw=data,
        )
