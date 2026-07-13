"""Key-field extraction for receipts and invoices from OCR text."""

from __future__ import annotations

import re

_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "invoice_number": [
        re.compile(r"\b(?:invoice|inv|receipt)\s*(?:no|number|#|num)?\s*[:.#]?\s*([A-Z]{0,4}[-/]?\d[\w/-]*)", re.I),
    ],
    "date": [
        re.compile(r"\b(\d{4}-\d{2}-\d{2})\b"),
        re.compile(r"\b(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})\b"),
        re.compile(
            r"\b(\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{2,4})\b",
            re.I,
        ),
    ],
    # `[|:$]*` also tolerates the cell separator produced by table_text().
    "total": [
        re.compile(r"(?:grand\s+total|amount\s+due|total\s+due|total)\s*[|:$]*\s*\$?\s*([\d,]+\.\d{2})", re.I),
    ],
    "tax": [
        re.compile(r"(?:tax|vat|gst)\s*(?:\(?\d{1,2}%\)?)?\s*[|:$]*\s*\$?\s*([\d,]+\.\d{2})", re.I),
    ],
    "vendor_tax_id": [
        re.compile(r"\b(?:ntn|vat\s*reg|tax\s*id|ein)\s*[:#]?\s*([\w-]{5,})", re.I),
    ],
}


def extract_receipt_fields(text: str) -> dict[str, str]:
    """Best-effort structured fields from receipt/invoice OCR text.

    Only fields actually found are returned; 'total' prefers the last match
    (grand total lines follow item lines on receipts).
    """
    fields: dict[str, str] = {}
    for name, patterns in _PATTERNS.items():
        for pattern in patterns:
            matches = pattern.findall(text)
            if matches:
                fields[name] = matches[-1] if name == "total" else matches[0]
                break
    return fields
