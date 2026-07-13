"""Embedding pipeline: pluggable providers + cache + batching service.

    from app.embeddings import EmbeddingService, create_provider

    service = EmbeddingService(create_provider("openai"), cache_path=Path("data/emb.db"))
    vectors = service.embed_texts([c.text for c in chunks])
    query_vec = service.embed_query("annual leave policy")
"""

from app.embeddings.base import (
    EmbeddingProvider,
    ProviderConfigurationError,
    ProviderRequestError,
)
from app.embeddings.cache import EmbeddingCache
from app.embeddings.registry import PROVIDERS, create_provider
from app.embeddings.service import EmbeddingService

__all__ = [
    "EmbeddingCache",
    "EmbeddingProvider",
    "EmbeddingService",
    "PROVIDERS",
    "ProviderConfigurationError",
    "ProviderRequestError",
    "create_provider",
]
