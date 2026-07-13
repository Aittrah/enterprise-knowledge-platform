"""Local BGE / E5 embeddings via sentence-transformers.

Retrieval-tuned local models require role prefixes on the *text itself* —
that formatting lives here as pure functions so it is testable without
torch installed.
"""

from __future__ import annotations

from app.embeddings.base import InputType, ProviderConfigurationError, Vector

_BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

_MODEL_ALIASES = {
    "bge": "BAAI/bge-small-en-v1.5",
    "e5": "intfloat/e5-small-v2",
}


def format_for_model(texts: list[str], model_name: str, input_type: InputType) -> list[str]:
    """Apply the model family's query/passage prefix convention."""
    lowered = model_name.lower()
    if "e5" in lowered:
        prefix = "query: " if input_type == "query" else "passage: "
        return [prefix + t for t in texts]
    if "bge" in lowered and input_type == "query":
        return [_BGE_QUERY_PREFIX + t for t in texts]
    return texts


class LocalSentenceTransformerProvider:
    name = "local"

    def __init__(self, model: str = "bge") -> None:
        self.model = _MODEL_ALIASES.get(model, model)
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise ProviderConfigurationError(
                "Local embeddings need `pip install sentence-transformers` "
                "(pulls in torch). Alternatively use the 'hashing' provider "
                "for keyless development."
            ) from exc
        self._model = SentenceTransformer(self.model)
        self.dimension = self._model.get_sentence_embedding_dimension()

    def embed(self, texts: list[str], input_type: InputType = "document") -> list[Vector]:
        formatted = format_for_model(texts, self.model, input_type)
        vectors = self._model.encode(formatted, normalize_embeddings=True)
        return [v.tolist() for v in vectors]
