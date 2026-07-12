"""CSV/TSV extraction: each row becomes a self-describing "header: value"

element so individual rows stay meaningful after chunking, plus one TABLE
element preserving the sheet as a whole."""

from __future__ import annotations

import csv
import io
from pathlib import Path

from charset_normalizer import from_bytes

from app.ingestion.extractors.base import BaseExtractor, ExtractionError
from app.ingestion.models import ElementType, ExtractedDocument, ExtractedElement

_MAX_TABLE_PREVIEW_ROWS = 200


class CsvExtractor(BaseExtractor):
    extensions = (".csv", ".tsv")
    file_type = "csv"

    def extract(self, path: Path) -> ExtractedDocument:
        doc = self._new_document(path)
        raw = path.read_bytes()
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            best = from_bytes(raw).best()
            if best is None:
                raise ExtractionError(f"Cannot detect encoding of {path.name}")
            text = str(best)
            doc.warnings.append(f"decoded as {best.encoding} (not utf-8)")

        sample = text[:4096]
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        except csv.Error:
            dialect = csv.excel
            if path.suffix.lower() == ".tsv":
                dialect.delimiter = "\t"
            doc.warnings.append("could not sniff dialect; assumed comma-separated")

        rows = list(csv.reader(io.StringIO(text), dialect))
        rows = [r for r in rows if any(cell.strip() for cell in r)]
        if not rows:
            doc.warnings.append("file contains no data rows")
            return doc

        header = [h.strip() for h in rows[0]]
        doc.native_properties["columns"] = header
        for i, row in enumerate(rows[1:], start=2):
            pairs = [
                f"{header[j] if j < len(header) else f'col{j + 1}'}: {cell.strip()}"
                for j, cell in enumerate(row)
                if cell.strip()
            ]
            if pairs:
                doc.elements.append(
                    ExtractedElement(ElementType.ROW, " | ".join(pairs), position=i)
                )

        preview = rows[: _MAX_TABLE_PREVIEW_ROWS + 1]
        doc.elements.append(
            ExtractedElement(
                ElementType.TABLE,
                "\n".join(" | ".join(cell.strip() for cell in r) for r in preview),
                extra={"rows": len(rows) - 1, "cols": len(header), "truncated": len(rows) - 1 > _MAX_TABLE_PREVIEW_ROWS},
            )
        )
        return doc
