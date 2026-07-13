"""Provider factory: name -> configured provider.

API keys come from the environment (.env) unless passed explicitly.
"""

from __future__ import annotations

from app.embeddings.base import EmbeddingProvider, ProviderConfigurationError
from app.embeddings.providers import (
    CohereProvider,
    HashingProvider,
    LocalSentenceTransformerProvider,
    OpenAIProvider,
    VoyageProvider,
)

PROVIDERS = ("openai", "cohere", "voyage", "bge", "e5", "hashing")


def create_provider(name: str, **kwargs) -> EmbeddingProvider:
    match name:
        case "openai":
            return OpenAIProvider(**kwargs)
        case "cohere":
            return CohereProvider(**kwargs)
        case "voyage":
            return VoyageProvider(**kwargs)
        case "bge" | "e5":
            return LocalSentenceTransformerProvider(model=name, **kwargs)
        case "hashing":
            return HashingProvider(**kwargs)
        case _:
            raise ProviderConfigurationError(
                f"Unknown embedding provider '{name}'. Choose from {PROVIDERS}"
            )
