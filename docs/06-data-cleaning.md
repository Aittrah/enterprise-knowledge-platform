# Milestone 6 — Data Cleaning

**Module:** `backend/app/processing/` · **Tests:** `backend/tests/test_cleaning.py` (16; suite 51)

## What it does

Sits between extraction/OCR and chunking, and runs automatically inside `IngestionPipeline` (disable with `clean=False`):

```
ExtractedDocument
  1. normalize      — NFKC (ligatures ﬁ→fi), smart quotes/dashes, soft hyphens,
                      line-break de-hyphenation, control chars, whitespace
  2. strip chrome   — headers/footers repeated across page edges
  3. drop boilerplate — bare "Page 3 of 12", separators, "CONFIDENTIAL" stamps
  4. deduplicate    — exact (hash) + near (MinHash) duplicate elements
  → CleaningStats recorded in native_properties["cleaning"]
```

## Header/footer detection

Lines at the top/bottom two lines of each page are fingerprinted (lowercased, digits masked so `Page 3 of 12` ≡ `Page 7 of 12`). A fingerprint seen on ≥ 60 % of pages (min 3) is chrome and is removed document-wide. Guards: documents under 3 pages are untouched, and lines over 80 chars are never chrome candidates — body text that happens to sit at a page boundary must survive.

## Deduplication engine

- **Exact:** sha256 of the case/whitespace-folded text. Digits are *not* masked — `id: 1` and `id: 2` are different content (this distinction was caught by a failing test during development).
- **Near:** MinHash (32 permutations, blake2b) over 5-word shingles estimating Jaccard similarity; default threshold 0.92 — catches the same policy paragraph re-pasted with a word changed.
- **Type-aware:** structured rows (CSV/table) are only ever exact-deduped; similar-looking rows are legitimate data, not duplicates.
- Candidate lookup is linear for now; the same signatures drop into MinHash-LSH banding when corpus size demands it (noted for M9).

The engine is exposed standalone (`DeduplicationEngine`) for cross-document dedup at the knowledge-base layer, and used internally for within-document element dedup.

## Why it matters downstream

Normalization improves both embedding quality and BM25 term matching (M8/M12); chrome and duplicate removal keep near-identical chunks from flooding top-k retrieval slots (M11–M13); cleaning stats surface in the Knowledge Base UI per document (Module 21).
