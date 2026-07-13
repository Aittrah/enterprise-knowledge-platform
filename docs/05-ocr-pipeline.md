# Milestone 5 — OCR Pipeline

**Module:** `backend/app/ingestion/ocr/` · **Tests:** `backend/tests/test_ocr.py` (15, engine-independent)

## What it does

Recovers text from scanned PDFs, images, receipts, and invoices, producing the same `ExtractedDocument` structure as native extractors — so everything downstream (cleaning, chunking, embedding) is format-blind.

```
image / scanned PDF
   └─> preprocess (orientation, grayscale, autocontrast, Otsu binarize, upscale)
   └─> engine.recognize() → positioned OcrWords            [pluggable engine]
   └─> layout: words → lines → blocks (paragraph | table)  [pure geometry]
   └─> tables: column clustering → aligned rows
   └─> fields: receipt/invoice key fields (number, date, total, tax)
   └─> ExtractedDocument with per-block confidence + warnings
```

## How each requirement is covered

| Requirement | Implementation |
|---|---|
| Scanned PDFs | `PdfExtractor` flags pages with no text layer; `IngestionPipeline` re-runs them through OCR automatically (`pdf_render.py` rasterizes via pypdfium2, no system dependency) |
| Images | `.png .jpg .jpeg .tif .tiff .bmp .webp` registered in the extractor registry → `ImageExtractor` → OCR |
| Receipts / invoices | `fields.py` extracts invoice number, date, total, tax, tax id from recognized text into `native_properties["receipt_fields"]` |
| Layout detection | `layout.py` clusters word boxes into lines (vertical center proximity) and blocks (line-gap segmentation) — engine-agnostic |
| Table extraction | `tables.py` splits lines on wide horizontal gaps and clusters cell x-positions into columns, padding ragged rows |

## Design decisions

- **Engine is a protocol, not a dependency.** `OcrEngine` = `is_available()` + `recognize(image) -> list[OcrWord]`. Tesseract is the default adapter; a cloud OCR (Azure Document Intelligence, Textract) plugs in later without touching layout/table code. Tests inject a fake engine, so CI needs no OCR binary.
- **Confidence is carried, not hidden.** Every block records mean word confidence; blocks under 60 % add a warning. This feeds the UI's groundedness/quality seals (Module 21) and evaluation (M22).
- **Graceful degradation.** Without the Tesseract binary, image ingestion raises a clear install hint, and scanned PDFs keep their "route to OCR" warning instead of failing the pipeline.

## Runtime requirement

Real OCR needs the Tesseract binary on the host:

- Windows: [UB Mannheim installer](https://github.com/UB-Mannheim/tesseract/wiki) or `choco install tesseract`
- The `test_tesseract_reads_rendered_text` smoke test un-skips automatically once installed.
