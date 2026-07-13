# Milestone 7 — Chunking Engine

**Module:** `backend/app/processing/chunking/` · **Tests:** `backend/tests/test_chunking.py` (24; suite 75)

## What it does

Turns a cleaned `ExtractedDocument` into retrieval-ready `Chunk`s with provenance metadata and validates the result before anything is embedded:

```python
from app.processing.chunking import ChunkGenerator, ChunkValidator

chunks = ChunkGenerator(strategy="semantic", max_tokens=512).generate(
    result.document, result.metadata
)
report = ChunkValidator(max_tokens=512).validate(chunks, result.document)
```

## Strategies

| Strategy | How it works | When to use |
|---|---|---|
| `semantic` (default) | Structure-aware grouping of typed elements: headings open chunks and build a breadcrumb, tables stay whole, prose splits on lexical-cohesion topic shifts | Documents with structure — the M4 extractors preserve exactly what this needs |
| `recursive` | Separator hierarchy (paragraph → line → sentence → word) with greedy re-merge up to budget | Unstructured prose |
| `token` | Fixed sliding window with overlap | Baseline / guaranteed size bounds |

### Semantic boundaries, in priority order

1. **Headings** — always start a new chunk; a run of consecutive headings stays together, and a heading directly above a table joins the table's chunk. The heading path (`["Employee Handbook", "Compensation"]`) is carried in metadata, giving retrieval and citations section context.
2. **Tables** — one chunk each, `keep_whole=True`, never split and exempt from size limits (a split table is garbage at retrieval time).
3. **Topic shifts** — consecutive prose splits when content-word Jaccard overlap falls below threshold and the chunk already has enough substance. The cohesion function is an injectable callable: at M8 an embedding-cosine version replaces the lexical default without touching this module.

Oversized prose groups fall back to recursive splitting while keeping their heading-path metadata.

## Metadata chunking

Every chunk carries: `source`, `title`, `version`, `sha256`, `strategy`, `heading_path`, `pages`, `element_types`. Chunk ids are deterministic (source + strategy + index + content hash) so re-ingestion upserts instead of duplicating vectors.

## Token counting

Sizing uses a fast word/punctuation heuristic behind a `TokenCounter` protocol; an exact tokenizer (tiktoken) is injected at M8 when the embedding provider fixes the real vocabulary.

## Validator

Catches problems before they cost embedding money: empty/duplicate chunks, oversize (with `keep_whole` exemption), undersize fragments, missing provenance metadata, non-contiguous indices, and **coverage** — unique chunk text must cover ≥ 70 % of the source, so a silently-dropping chunker cannot ship. Returns a `ValidationReport` with issues and stats (count, avg/min/max tokens, coverage).
