"""GraphRAG: fuse knowledge-graph traversal with vector retrieval.

Vector search answers "what text sounds like the query"; the graph answers
"what is *connected* to the things the query names". GraphRAG runs both:

  1. extract entities from the query and match them to graph nodes
  2. expand neighbors (depth-limited) to collect related entities,
     relation evidence, and the documents they are MENTIONED_IN
  3. run a second retrieval scoped to those graph-implicated documents,
     with the query enriched by related entity names
  4. RRF-fuse the vector leg and the graph leg

The graph context (entities, relations with evidence) rides along in
``debug["graph_context"]`` so the AI layer can cite relationships, not
just passages.
"""

from __future__ import annotations

import time

from app.graph.entities import EntityExtractor
from app.retrieval.base import RetrievalResult, RetrievedChunk, Retriever
from app.retrieval.fusion import reciprocal_rank_fusion
from app.stores.base import Filters


class GraphRAGRetriever:
    name = "graphrag"

    def __init__(
        self,
        retriever: Retriever,
        graph_store,
        extractor: EntityExtractor | None = None,
        # 2 hops: query entity -> shared entity -> that entity's documents.
        # Depth 1 would only ever find documents the query entity itself
        # appears in, which plain retrieval already covers.
        depth: int = 2,
        candidates: int = 30,
        rrf_k: int = 60,
    ) -> None:
        self._retriever = retriever
        self._graph = graph_store
        self._extractor = extractor or EntityExtractor()
        self._depth = depth
        self._candidates = candidates
        self._rrf_k = rrf_k

    def retrieve(
        self, query: str, top_k: int = 8, filters: Filters | None = None
    ) -> RetrievalResult:
        started = time.perf_counter()

        vector_leg = self._retriever.retrieve(query, top_k=self._candidates, filters=filters)

        matched, related, relations, documents = self._graph_context(query)

        graph_leg_chunks: list[RetrievedChunk] = []
        if documents:
            graph_filters = dict(filters or {})
            graph_filters["source"] = sorted(documents)
            enriched_query = " ".join([query, *sorted(related)])
            graph_leg_chunks = self._retriever.retrieve(
                enriched_query, top_k=self._candidates, filters=graph_filters
            ).chunks

        payloads = {c.id: c for c in vector_leg.chunks}
        payloads.update({c.id: c for c in graph_leg_chunks})

        fused = reciprocal_rank_fusion(
            {
                "vector": [c.id for c in vector_leg.chunks],
                "graph": [c.id for c in graph_leg_chunks],
            },
            k=self._rrf_k,
        )[:top_k]

        top_score = fused[0].score if fused else 1.0
        chunks = []
        for item in fused:
            chunk = payloads[item.id]
            chunk.metadata["fusion_ranks"] = item.ranks
            chunk.score = round(item.score / top_score, 4)
            chunks.append(chunk)

        return RetrievalResult(
            query=query,
            chunks=chunks,
            strategy=self.name,
            elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
            debug={
                "matched_entities": sorted(matched),
                "related_entities": sorted(related),
                "graph_documents": sorted(documents),
                "graph_context": relations,
                "vector_candidates": len(vector_leg.chunks),
                "graph_candidates": len(graph_leg_chunks),
            },
        )

    def _graph_context(self, query: str):
        """Match query entities to the graph and expand their neighborhood."""
        matched: set[str] = set()
        related: set[str] = set()
        relations: list[dict] = []
        documents: set[str] = set()

        query_entities = self._extractor.extract(query)
        seeds = {e.text for e in query_entities}
        # Fall back to matching graph node names against query words when
        # extraction finds nothing (lowercase mentions of known entities).
        if not seeds:
            for word in {w for w in query.split() if len(w) > 3}:
                for node in self._graph.search_nodes(word):
                    seeds.add(node.text if hasattr(node, "text") else node["name"])

        for seed in seeds:
            for node in self._graph.search_nodes(seed):
                key = node.key if hasattr(node, "key") else node["key"]
                label = node.text if hasattr(node, "text") else node["name"]
                matched.add(label)
                neighborhood = self._graph.neighbors(key, depth=self._depth)
                for entity in neighborhood["nodes"]:
                    if entity.type == "document":
                        documents.add(entity.source)
                    elif entity.key != key:
                        related.add(entity.text)
                for edge in neighborhood["edges"]:
                    if edge.type == "MENTIONED_IN":
                        documents.add(edge.source_document)
                        continue
                    relations.append(
                        {
                            "source": edge.source_key,
                            "target": edge.target_key,
                            "type": edge.type,
                            "evidence": edge.evidence,
                        }
                    )
                    documents.add(edge.source_document)

        documents.discard("")
        return matched, related, relations, documents
