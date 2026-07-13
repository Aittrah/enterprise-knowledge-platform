"""OCR engine contract and the Tesseract implementation.

Any engine that turns an image into positioned words can back the pipeline
(cloud OCR services plug in here later without touching layout/tables).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from PIL.Image import Image


class OcrEngineUnavailableError(Exception):
    """The configured OCR engine cannot run on this machine."""


@dataclass
class OcrWord:
    """One recognized word with its bounding box (pixels) and confidence (0-100)."""

    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    confidence: float

    @property
    def height(self) -> float:
        return self.y1 - self.y0

    @property
    def y_center(self) -> float:
        return (self.y0 + self.y1) / 2


@runtime_checkable
class OcrEngine(Protocol):
    name: str

    def is_available(self) -> bool: ...

    def recognize(self, image: "Image") -> list[OcrWord]: ...


class TesseractEngine:
    """pytesseract adapter. Requires the Tesseract binary
    (Windows: https://github.com/UB-Mannheim/tesseract/wiki, or `choco install tesseract`)."""

    name = "tesseract"

    def __init__(self, lang: str = "eng") -> None:
        self._lang = lang

    def is_available(self) -> bool:
        try:
            import pytesseract

            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False

    def recognize(self, image: "Image") -> list[OcrWord]:
        import pytesseract

        if not self.is_available():
            raise OcrEngineUnavailableError(
                "Tesseract binary not found. Install it from "
                "https://github.com/UB-Mannheim/tesseract/wiki (Windows) "
                "or `choco install tesseract`, then re-run."
            )

        data = pytesseract.image_to_data(
            image, lang=self._lang, output_type=pytesseract.Output.DICT
        )
        words: list[OcrWord] = []
        for i, text in enumerate(data["text"]):
            text = text.strip()
            conf = float(data["conf"][i])
            if not text or conf < 0:  # conf == -1 marks non-word boxes
                continue
            x, y = data["left"][i], data["top"][i]
            w, h = data["width"][i], data["height"][i]
            words.append(OcrWord(text, x, y, x + w, y + h, conf))
        return words
