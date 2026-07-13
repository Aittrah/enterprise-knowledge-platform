"""Image preparation before recognition: orientation, grayscale, contrast,

Otsu binarization, and upscaling of low-resolution scans."""

from __future__ import annotations

from PIL import Image, ImageOps

_MIN_LONG_EDGE = 1500  # below this, receipts/phone photos OCR poorly


def otsu_threshold(image: Image.Image) -> int:
    """Otsu's method on the grayscale histogram."""
    hist = image.histogram()[:256]
    total = sum(hist)
    if total == 0:
        return 127
    sum_all = sum(i * h for i, h in enumerate(hist))
    sum_bg = 0.0
    weight_bg = 0
    best_threshold, best_variance = 127, -1.0
    for t in range(256):
        weight_bg += hist[t]
        if weight_bg == 0:
            continue
        weight_fg = total - weight_bg
        if weight_fg == 0:
            break
        sum_bg += t * hist[t]
        mean_bg = sum_bg / weight_bg
        mean_fg = (sum_all - sum_bg) / weight_fg
        variance = weight_bg * weight_fg * (mean_bg - mean_fg) ** 2
        if variance > best_variance:
            best_variance, best_threshold = variance, t
    return best_threshold


def preprocess(image: Image.Image, binarize: bool = True) -> Image.Image:
    """Return an OCR-ready copy of *image*."""
    img = ImageOps.exif_transpose(image)
    img = img.convert("L")
    img = ImageOps.autocontrast(img)

    if max(img.size) < _MIN_LONG_EDGE:
        scale = _MIN_LONG_EDGE / max(img.size)
        img = img.resize(
            (round(img.width * scale), round(img.height * scale)), Image.LANCZOS
        )

    if binarize:
        threshold = otsu_threshold(img)
        img = img.point(lambda p: 255 if p > threshold else 0)
    return img
