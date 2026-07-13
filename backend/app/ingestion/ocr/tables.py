"""Table reconstruction from a table-classified layout block.

Cell x-positions are clustered into columns so ragged rows still align.
"""

from __future__ import annotations

from app.ingestion.ocr.layout import Block


def block_to_table_rows(block: Block) -> list[list[str]]:
    """Return the block's lines as rows of column-aligned cell texts."""
    gap = block.extra.get("cell_gap", 20.0)
    columns: list[float] = []  # representative x-start per column

    def column_index(x0: float) -> int:
        for i, cx in enumerate(columns):
            if abs(x0 - cx) <= gap * 2:
                columns[i] = (cx + x0) / 2  # drift toward the running mean
                return i
        columns.append(x0)
        return len(columns) - 1

    raw_rows: list[dict[int, str]] = []
    for line in block.lines:
        row: dict[int, str] = {}
        groups: list[list] = [[line.words[0]]]
        for prev, word in zip(line.words, line.words[1:]):
            if word.x0 - prev.x1 > gap:
                groups.append([word])
            else:
                groups[-1].append(word)
        for group in groups:
            idx = column_index(group[0].x0)
            text = " ".join(w.text for w in group)
            row[idx] = f"{row[idx]} {text}".strip() if idx in row else text
        raw_rows.append(row)

    # Order columns left-to-right and pad every row to the full width.
    order = sorted(range(len(columns)), key=columns.__getitem__)
    remap = {old: new for new, old in enumerate(order)}
    width = len(columns)
    rows: list[list[str]] = []
    for raw in raw_rows:
        cells = [""] * width
        for old_idx, text in raw.items():
            cells[remap[old_idx]] = text
        rows.append(cells)
    return rows


def table_text(block: Block) -> str:
    return "\n".join(" | ".join(row) for row in block_to_table_rows(block))
