"""Render PDF pages to images for OCR (pypdfium2 — no system dependency)."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

from PIL import Image


def render_pdf_pages(path: Path, dpi: int = 200) -> Iterator[tuple[int, Image.Image]]:
    """Yield (1-based page number, PIL image) for every page of *path*."""
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(str(path))
    try:
        scale = dpi / 72  # PDF user space is 72 dpi
        for i, page in enumerate(pdf, start=1):
            bitmap = page.render(scale=scale)
            try:
                yield i, bitmap.to_pil()
            finally:
                bitmap.close()
                page.close()
    finally:
        pdf.close()
