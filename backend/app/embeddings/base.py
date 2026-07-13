"""Embedding provider contract.

``input_type`` matters: retrieval-tuned models (E5, BGE, Cohere, Voyage)
embed queries and documents differently — either via an API parameter or a
text prefix. Callers always say which side they are embedding; each adapter
translates that to its provider's convention.
"""

from __future__ import annotations

from typing import Literal, Protocol, runtime_checkable

InputType = Literal["document", "query"]

Vector = list[float]


class ProviderConfigurationError(Exception):
    """Provider cannot be constructed (missing API key, missing package)."""


class ProviderRequestError(Exception):
    """A provider call failed (network, auth, rate limit). Retryable."""


@runtime_checkable
class EmbeddingProvider(Protocol):
    name: str
    model: str
    dimension: int

    def embed(self, texts: list[str], input_type: InputType = "document") -> list[Vector]:
        """Embed *texts* in order. Must return one vector per input."""
        ...
