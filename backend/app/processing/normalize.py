"""Text normalization.

Extraction and OCR leave artifacts — ligatures, smart quotes, soft hyphens,
line-break hyphenation, stray control characters, ragged whitespace — that
hurt both embedding quality and BM25 term matching. Everything here is
meaning-preserving.
"""

from __future__ import annotations

import re
import unicodedata

# C0/C1 control characters except \t and \n.
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")
# A word broken across a line ("infor-\nmation" -> "information").
_LINEBREAK_HYPHEN = re.compile(r"(\w)-[ \t]*\n[ \t]*(\w)")
_SPACES = re.compile(r"[ \t]+")
_MANY_NEWLINES = re.compile(r"\n{3,}")

_CHAR_MAP = str.maketrans(
    {
        "“": '"', "”": '"', "„": '"', "«": '"', "»": '"',
        "‘": "'", "’": "'", "‚": "'",
        "–": "-", "—": "-", "―": "-", "−": "-",
        " ": " ", " ": " ", " ": " ",  # non-breaking spaces
        "­": None,  # soft hyphen
        "​": None, "‌": None, "‍": None, "﻿": None,  # zero-width
        "…": "...",
    }
)


def normalize_text(text: str) -> str:
    """Return a normalized copy of *text* (safe to call twice)."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _LINEBREAK_HYPHEN.sub(r"\1\2", text)
    # NFKC folds ligatures (ﬁ -> fi), fullwidth forms, and compatibility chars.
    text = unicodedata.normalize("NFKC", text)
    text = text.translate(_CHAR_MAP)
    text = _CONTROL.sub("", text)
    text = _SPACES.sub(" ", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    text = _MANY_NEWLINES.sub("\n\n", text)
    return text.strip()
