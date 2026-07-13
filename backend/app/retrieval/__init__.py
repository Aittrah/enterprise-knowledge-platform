"""Retrieval layer.

M11: dense semantic retrieval (this module)
M12: hybrid BM25 + vector + RRF        M13: reranking        M14: GraphRAG

All retrievers share the ``Retriever`` contract, so the AI layer (M15+)
composes them without caring which strategy is active.
"""

from app.retrieval.base import RetrievalResult, RetrievedChunk, Retriever
from app.retrieval.dense import DenseRetriever

__all__ = ["DenseRetriever", "RetrievalResult", "RetrievedChunk", "Retriever"]
