"""In-memory graph store: the GraphStore contract's reference

implementation, offline dev backend, and the source of visualization data.
"""

from __future__ import annotations

from collections import deque

from app.graph.entities import Entity
from app.graph.relations import Relation


class InMemoryGraphStore:
    def __init__(self) -> None:
        self._entities: dict[str, Entity] = {}
        self._relations: dict[str, Relation] = {}

    # -- writes -----------------------------------------------------------------

    def upsert_entities(self, entities: list[Entity]) -> None:
        for entity in entities:
            existing = self._entities.get(entity.key)
            if existing:
                existing.mentions += entity.mentions
            else:
                self._entities[entity.key] = entity

    def upsert_relations(self, relations: list[Relation]) -> None:
        for relation in relations:
            self._relations.setdefault(relation.key, relation)

    def delete_by_source(self, source: str) -> None:
        self._relations = {
            k: r for k, r in self._relations.items() if r.source_document != source
        }
        self._entities = {
            k: e for k, e in self._entities.items() if e.source != source
        }

    # -- reads --------------------------------------------------------------------

    def search_nodes(self, term: str) -> list[Entity]:
        term = term.lower()
        return [e for e in self._entities.values() if term in e.text.lower()]

    def neighbors(self, entity_key: str, depth: int = 1) -> dict:
        """BFS neighborhood: the payload behind the UI's expand-node action."""
        seen = {entity_key}
        edges: list[Relation] = []
        frontier = deque([(entity_key, 0)])
        while frontier:
            key, level = frontier.popleft()
            if level >= depth:
                continue
            for relation in self._relations.values():
                if key not in (relation.source_key, relation.target_key):
                    continue
                other = (
                    relation.target_key
                    if relation.source_key == key
                    else relation.source_key
                )
                edges.append(relation)
                if other not in seen:
                    seen.add(other)
                    frontier.append((other, level + 1))
        nodes = [self._entities[k] for k in seen if k in self._entities]
        unique_edges = {r.key: r for r in edges}
        return {"nodes": nodes, "edges": list(unique_edges.values())}

    def stats(self) -> dict:
        by_type: dict[str, int] = {}
        for entity in self._entities.values():
            by_type[entity.type] = by_type.get(entity.type, 0) + 1
        return {
            "entities": len(self._entities),
            "relations": len(self._relations),
            "entities_by_type": by_type,
        }

    # -- visualization ---------------------------------------------------------------

    def to_visualization(self) -> dict:
        """Force-graph-ready JSON for the Module 21 GraphViewer."""
        degree: dict[str, int] = {}
        for relation in self._relations.values():
            degree[relation.source_key] = degree.get(relation.source_key, 0) + 1
            degree[relation.target_key] = degree.get(relation.target_key, 0) + 1
        return {
            "nodes": [
                {
                    "id": e.key,
                    "label": e.text,
                    "type": e.type,
                    "mentions": e.mentions,
                    "degree": degree.get(e.key, 0),
                }
                for e in self._entities.values()
            ],
            "edges": [
                {
                    "source": r.source_key,
                    "target": r.target_key,
                    "type": r.type,
                    "evidence": r.evidence,
                }
                for r in self._relations.values()
            ],
        }
