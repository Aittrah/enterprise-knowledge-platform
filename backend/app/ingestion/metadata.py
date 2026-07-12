"""Metadata generation: combines filesystem facts (size, hash, mtime) with

properties the document reports about itself (title, author)."""

from __future__ import annotations

import hashlib
import mimetypes
from datetime import datetime, timezone
from pathlib import Path

from app.ingestion.models import DocumentMetadata, ExtractedDocument

_HASH_CHUNK = 1 << 20  # 1 MiB


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(_HASH_CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def generate_metadata(path: Path, extracted: ExtractedDocument) -> DocumentMetadata:
    stat = path.stat()
    props = extracted.native_properties
    return DocumentMetadata(
        filename=path.name,
        file_type=extracted.file_type,
        size_bytes=stat.st_size,
        sha256=sha256_file(path),
        mime_type=mimetypes.guess_type(path.name)[0],
        title=props.get("title") or path.stem,
        author=props.get("author"),
        page_count=extracted.page_count,
        element_count=len(extracted.elements),
        modified_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
        extra={
            "warnings": list(extracted.warnings),
            "native_properties": {k: v for k, v in props.items() if v},
        },
    )
