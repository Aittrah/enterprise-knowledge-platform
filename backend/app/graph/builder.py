"""GraphBuilder: document -> entities -> relations -> graph store.

Every extracted entity is also linked to its source document with a
MENTIONED_IN edge, so graph traversal can always route back to citable
material — the bridge GraphRAG (M14) walks across.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.graph.entities import Entity, EntityExtractor
from app.graph.relations import Relation, RelationDetector
from app.ingestion.models import DocumentMetadata, ExtractedDocument


@dataclass
class GraphReport:
    source: str
    entities: int
    relations: int
    entities_by_type: dict[str, int]


class GraphBuilder:
    def __init__(
        self,
        store,
        extractor: EntityExtractor | None = None,
        detector: RelationDetector | None = None,
    ) -> None:
        self.store = store
        self._extractor = extractor or EntityExtractor()
        self._detector = detector or RelationDetector()

    def build(
        self, document: ExtractedDocument, metadata: DocumentMetadata
    ) -> GraphReport:
        source = metadata.filename

        # Re-building a document replaces its part of the graph.
        self.store.delete_by_source(source)

        text = document.text
        entities = self._extractor.extract(text, source=source)
        relations = self._detector.detect(text, entities, source_document=source)

        doc_entity = Entity(text=metadata.title or source, type="document", source=source)
        mentioned_in = [
            Relation(
                source_key=e.key,
                target_key=doc_entity.key,
                type="MENTIONED_IN",
                evidence=f"extracted from {source}",
                source_document=source,
            )
            for e in entities
        ]

        self.store.upsert_entities([*entities, doc_entity])
        self.store.upsert_relations([*relations, *mentioned_in])

        by_type: dict[str, int] = {}
        for entity in entities:
            by_type[entity.type] = by_type.get(entity.type, 0) + 1
        return GraphReport(
            source=source,
            entities=len(entities),
            relations=len(relations) + len(mentioned_in),
            entities_by_type=by_type,
        )
