# Milestone 10 — Knowledge Graph

**Module:** `backend/app/graph/` · **Tests:** `backend/tests/test_graph.py` (18; suite 131 + 2 live-integration)

## What it does

Builds a queryable graph of people, departments, organizations, amounts, dates, and documents from ingested content:

```python
from app.graph import GraphBuilder, InMemoryGraphStore  # or Neo4jGraphStore

builder = GraphBuilder(InMemoryGraphStore())
report = builder.build(result.document, result.metadata)
builder.store.neighbors("person:sara khan", depth=2)   # expand-node payload
builder.store.to_visualization()                       # force-graph JSON for the UI
```

## Entity extraction (`entities.py`)

Rule-based and fully offline: emails, money, dates by regex; organizations by capitalized-sequence + corporate suffix; people by honorific pattern or capitalized bigram behind a stoplist; departments by gazetteer. Strong patterns claim their text spans first so `Acme Corp` can never double-extract as a person. Repeated mentions increment a counter instead of duplicating.

**Precision over recall by design** — a noisy graph is worse than a sparse one. The Phase 5 LLM extractor plugs in behind the same `Entity` model to raise recall.

## Relation detection (`relations.py`)

Entities sharing a sentence are classified by verb cues between their mentions:

| Cue | Relation | Types |
|---|---|---|
| "reports to" | `REPORTS_TO` | person → person |
| "works in / joined / member of" | `WORKS_IN` | person → department |
| "works for / employed by" | `EMPLOYED_BY` | person → organization |
| "heads / leads / manages" | `MANAGES` | person → department |
| "signed / approved / authorized" | `APPROVED` | person → money |
| *(no cue)* | `CO_OCCURS` | only meaningful type pairs |

**Every edge stores its evidence sentence** — the graph can always answer "why is this edge here?", which feeds the provenance UI and the compliance use case (UC-3).

## Storage

- **`Neo4jGraphStore`** — HTTP transaction API via httpx (basic auth, MockTransport-tested, no driver). Labels and relationship types are interpolated into Cypher, which Neo4j cannot parameterize, so both pass whitelists — `EVIL; DROP` is rejected, not executed.
- **`InMemoryGraphStore`** — reference implementation + offline dev: BFS `neighbors(key, depth)`, substring `search_nodes`, per-source delete, stats by type.

## GraphBuilder

`delete_by_source` → extract → detect → upsert, plus a `Document` node with `MENTIONED_IN` edges from every entity — the bridge GraphRAG (M14) walks from graph hits back to citable chunks. Rebuilding a document replaces its subgraph instead of duplicating it.

## Visualization

`to_visualization()` emits force-graph-ready JSON: nodes carry `label/type/mentions/degree` (the UI sizes and colors by these), edges carry `type` and `evidence` (hover tooltip). This is the data contract for Module 21's GraphViewer screen.
