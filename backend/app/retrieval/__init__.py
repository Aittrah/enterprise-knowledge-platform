"""Retrieval layer.

M11: dense semantic retrieval (this module)
M12: hybrid BM25 + vector + RRF        M13: reranking        M14: GraphRAG

All retrievers share the ``Retriever`` contract, so the AI layer (M15+)
composes them without caring which strategy is active.
"""

from app.retrieval.base import RetrievalResult, RetrievedChunk, Retriever
from app.retrieval.bm25 import BM25Index
from app.retrieval.dense import DenseRetriever
from app.retrieval.fusion import reciprocal_rank_fusion
from app.retrieval.graphrag import GraphRAGRetriever
from app.retrieval.hybrid import HybridRetriever
from app.retrieval.rerank import (
    CohereReranker,
    CrossEncoderReranker,
    LexicalReranker,
    RerankedRetriever,
    Reranker,
)

__all__ = [
    "BM25Index",
    "CohereReranker",
    "CrossEncoderReranker",
    "DenseRetriever",
    "GraphRAGRetriever",
    "HybridRetriever",
    "LexicalReranker",
    "RerankedRetriever",
    "Reranker",
    "RetrievalResult",
    "RetrievedChunk",
    "Retriever",
    "reciprocal_rank_fusion",
]
