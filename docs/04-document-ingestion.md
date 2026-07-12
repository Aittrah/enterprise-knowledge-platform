# Milestone 4 — Document Ingestion

**Module:** `backend/app/ingestion/` · **Tests:** `backend/tests/` (21 passing)

## What it does

Turns a source file into structured, chunkable content plus system metadata and a version record:

```
file ──> extractor (by extension) ──> ExtractedDocument (typed elements)
                                        ├─> generate_metadata()  → DocumentMetadata (sha256, mime, props)
                                        └─> VersionTracker.register() → VersionInfo (v1, v2, duplicate?)
```

Usage:

```python
from app.ingestion import IngestionPipeline

pipeline = IngestionPipeline(Path("data/versions.json"))
result = pipeline.ingest("handbook.docx")
result.document.text        # plain text
result.document.tables      # structured tables
result.metadata.sha256      # content hash
result.version.version      # 1, 2, ...
result.skipped_duplicate    # True if identical bytes already ingested
```

## Supported formats

| Format | Library | Structure captured |
|---|---|---|
| PDF | pypdf | per-page text, PDF info dict; flags scanned PDFs for the M5 OCR route |
| DOCX | python-docx | headings w/ levels, paragraphs, list items, tables in document order, core properties |
| TXT/MD | charset-normalizer | blank-line paragraphs, non-UTF-8 encoding detection |
| HTML | BeautifulSoup + lxml | `<title>`, h1–h6 with level, paragraphs, list items, tables; script/style/nav stripped |
| CSV/TSV | stdlib csv | dialect sniffing; each row as self-describing `header: value` pairs + whole-sheet table |
| PPTX | python-pptx | slide titles, body text, tables, speaker notes, positioned by slide |

## Design decisions

- **Elements, not blobs.** Extractors emit typed `ExtractedElement`s (heading/paragraph/table/row/notes with position). The M7 chunking engine needs structure — flattening to a string here would throw away exactly what semantic chunking uses.
- **CSV rows are self-describing** (`invoice_id: INV-001 | vendor: Acme`) so a single row remains meaningful after chunking and retrieval.
- **Warnings, not failures.** Recoverable issues (encoding fallback, empty pages, unsniffable dialect) are recorded on the document; only unreadable files raise `ExtractionError`.
- **Scanned-PDF detection.** A PDF with no text layer on any page gets a `route to OCR` warning — the M5 pipeline hook.
- **Version tracking is content-addressed.** sha256 identity: identical bytes → duplicate (skip re-embedding cost), changed bytes → next version (supersedes prior chunks downstream). JSON store now; same interface re-backed by PostgreSQL at M9.
