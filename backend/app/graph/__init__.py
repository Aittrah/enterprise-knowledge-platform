"""Knowledge graph: entities, relations, Neo4j storage, visualization.

    from app.graph import GraphBuilder, InMemoryGraphStore

    builder = GraphBuilder(InMemoryGraphStore())
    report = builder.build(document, metadata)
    viz = builder.store.to_visualization()   # nodes + edges for the UI

Extraction is rule-based (patterns + gazetteers) in this milestone; the
LLM-based extractor upgrades it in Phase 5 behind the same interfaces.
"""

from app.graph.builder import GraphBuilder, GraphReport
from app.graph.entities import Entity, EntityExtractor
from app.graph.memory import InMemoryGraphStore
from app.graph.neo4j_store import Neo4jGraphStore
from app.graph.relations import Relation, RelationDetector

__all__ = [
    "Entity",
    "EntityExtractor",
    "GraphBuilder",
    "GraphReport",
    "InMemoryGraphStore",
    "Neo4jGraphStore",
    "Relation",
    "RelationDetector",
]
