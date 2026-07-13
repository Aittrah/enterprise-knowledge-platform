"""Context formatting: retrieved chunks -> numbered, citable blocks.

The numbering here is the citation contract: ``[n]`` in the model's answer
must resolve through the returned citation map to a real retrieved chunk —
guardrails (M20) verify exactly that.
"""

from __future__ import annotations

from app.retrieval.base import RetrievedChunk


def format_context(
    chunks: list[RetrievedChunk],
) -> tuple[str, dict[int, RetrievedChunk]]:
    """Render chunks as numbered source blocks; return (text, citation_map)."""
    blocks = []
    citation_map: dict[int, RetrievedChunk] = {}
    for number, chunk in enumerate(chunks, start=1):
        citation_map[number] = chunk
        heading = " > ".join(chunk.metadata.get("heading_path") or [])
        pages = chunk.metadata.get("pages") or []
        location = ", ".join(
            part
            for part in (
                f"section: {heading}" if heading else "",
                f"pages: {', '.join(map(str, pages))}" if pages else "",
            )
            if part
        )
        header = f"[{number}] {chunk.source}" + (f" ({location})" if location else "")
        blocks.append(f"{header}\n{chunk.text}")
    return "\n\n---\n\n".join(blocks), citation_map


def format_graph_context(relations: list[dict]) -> str:
    """Render GraphRAG relations as citable facts with their evidence."""
    if not relations:
        return ""
    lines = []
    for relation in relations:
        source = relation["source"].split(":", 1)[-1]
        target = relation["target"].split(":", 1)[-1]
        lines.append(
            f"- {source} —{relation['type']}→ {target} (evidence: \"{relation['evidence']}\")"
        )
    return "Known relationships from the knowledge graph:\n" + "\n".join(lines)
