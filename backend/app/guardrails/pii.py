"""PII detection and masking.

Runs over model output (and optionally ingested text). Credit cards are
Luhn-validated so 16-digit invoice numbers don't false-positive.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_PATTERNS: dict[str, re.Pattern[str]] = {
    "email": re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]{2,}\b"),
    "phone": re.compile(
        r"(?<![\d-])(?:\+?\d{1,3}[\s.-]?)?(?:\(\d{2,4}\)[\s.-]?)?\d{3,4}[\s.-]\d{3,4}(?:[\s.-]\d{2,4})?(?![\d-])"
    ),
    "credit_card": re.compile(r"\b(?:\d[ -]?){13,19}\b"),
    "national_id": re.compile(r"\b\d{5}-\d{7}-\d\b|\b\d{3}-\d{2}-\d{4}\b"),  # CNIC / SSN
    "iban": re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b"),
}


def _luhn_ok(digits: str) -> bool:
    total = 0
    for index, char in enumerate(reversed(digits)):
        value = int(char)
        if index % 2 == 1:
            value *= 2
            if value > 9:
                value -= 9
        total += value
    return total % 10 == 0


@dataclass
class PIIMatch:
    type: str
    value: str
    masked: str


class PIIDetector:
    def detect(self, text: str) -> list[PIIMatch]:
        matches: list[PIIMatch] = []
        for pii_type, pattern in _PATTERNS.items():
            for found in pattern.finditer(text):
                value = found.group()
                if pii_type == "credit_card":
                    digits = re.sub(r"\D", "", value)
                    if not (13 <= len(digits) <= 19 and _luhn_ok(digits)):
                        continue
                matches.append(
                    PIIMatch(type=pii_type, value=value, masked=self._mask(pii_type, value))
                )
        return matches

    def mask(self, text: str) -> tuple[str, list[PIIMatch]]:
        matches = self.detect(text)
        for match in matches:
            text = text.replace(match.value, match.masked)
        return text, matches

    @staticmethod
    def _mask(pii_type: str, value: str) -> str:
        if pii_type == "email":
            local, _, domain = value.partition("@")
            return f"{local[0]}***@{domain}"
        digits = re.sub(r"\D", "", value)
        tail = digits[-4:] if len(digits) >= 4 else "****"
        return f"[{pii_type}:…{tail}]"
