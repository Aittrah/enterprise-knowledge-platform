"""Layout detection from word geometry.

Words -> lines (vertical clustering) -> blocks (line-gap segmentation),
with each block classified as paragraph or table candidate based on
consistent wide horizontal gaps across its lines.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import median

from app.ingestion.ocr.engine import OcrWord

# A gap wider than this many median-word-heights splits a line into cells.
_CELL_GAP_FACTOR = 1.5
# A vertical gap taller than this many line heights starts a new block.
_BLOCK_GAP_FACTOR = 1.8
# Minimum share of multi-cell lines for a block to count as a table.
_TABLE_LINE_SHARE = 0.6


@dataclass
class Line:
    words: list[OcrWord]

    @property
    def text(self) -> str:
        return " ".join(w.text for w in self.words)

    @property
    def y0(self) -> float:
        return min(w.y0 for w in self.words)

    @property
    def y1(self) -> float:
        return max(w.y1 for w in self.words)

    @property
    def height(self) -> float:
        return self.y1 - self.y0

    def cells(self, gap: float) -> list[str]:
        """Split the line into cell texts wherever the horizontal gap exceeds *gap*."""
        groups: list[list[OcrWord]] = [[self.words[0]]]
        for prev, word in zip(self.words, self.words[1:]):
            if word.x0 - prev.x1 > gap:
                groups.append([word])
            else:
                groups[-1].append(word)
        return [" ".join(w.text for w in g) for g in groups]


@dataclass
class Block:
    lines: list[Line]
    kind: str = "paragraph"  # or "table"
    extra: dict = field(default_factory=dict)

    @property
    def text(self) -> str:
        return "\n".join(line.text for line in self.lines)


def group_lines(words: list[OcrWord]) -> list[Line]:
    """Cluster words into reading-order lines by vertical center proximity."""
    if not words:
        return []
    words = sorted(words, key=lambda w: (w.y_center, w.x0))
    lines: list[list[OcrWord]] = [[words[0]]]
    for word in words[1:]:
        current = lines[-1]
        line_center = sum(w.y_center for w in current) / len(current)
        line_height = median(w.height for w in current)
        if abs(word.y_center - line_center) <= line_height / 2:
            current.append(word)
        else:
            lines.append([word])
    return [Line(sorted(ws, key=lambda w: w.x0)) for ws in lines]


def _cell_gap(lines: list[Line]) -> float:
    heights = [w.height for line in lines for w in line.words]
    return _CELL_GAP_FACTOR * median(heights) if heights else 20.0


def group_blocks(lines: list[Line]) -> list[Block]:
    """Segment lines into blocks and classify each as paragraph or table."""
    if not lines:
        return []
    blocks: list[list[Line]] = [[lines[0]]]
    for prev, line in zip(lines, lines[1:]):
        gap = line.y0 - prev.y1
        threshold = _BLOCK_GAP_FACTOR * max(prev.height, line.height)
        if gap > threshold:
            blocks.append([line])
        else:
            blocks[-1].append(line)
    return [_classify(Block(ls)) for ls in blocks]


def _classify(block: Block) -> Block:
    """A block whose lines consistently split into the same number of
    multiple cells reads as a table."""
    if len(block.lines) < 2:
        return block
    gap = _cell_gap(block.lines)
    cell_counts = [len(line.cells(gap)) for line in block.lines]
    multi = [c for c in cell_counts if c >= 2]
    if len(multi) / len(cell_counts) >= _TABLE_LINE_SHARE:
        block.kind = "table"
        block.extra["cell_gap"] = gap
        block.extra["columns"] = max(set(multi), key=multi.count)
    return block
