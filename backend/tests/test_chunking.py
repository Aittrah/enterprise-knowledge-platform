from pathlib import Path

import pytest

from app.ingestion.extractors import extract
from app.ingestion.models import ElementType, ExtractedDocument, ExtractedElement
from app.processing.chunking import Chunk, ChunkGenerator, ChunkValidator
from app.processing.chunking.recursive import RecursiveChunker
from app.processing.chunking.semantic import SemanticChunker, lexical_cohesion
from app.processing.chunking.token_chunker import TokenChunker
from app.processing.chunking.tokens import HeuristicTokenCounter

COUNTER = HeuristicTokenCounter()

HR_SENTENCE = (
    "Employees receive annual leave benefits including paid vacation days "
    "accrued monthly under the leave policy. "
)
FINANCE_SENTENCE = (
    "Quarterly revenue projections indicate strong fiscal growth across "
    "regional markets and product portfolios. "
)


def heading(text: str, level: int = 1) -> ExtractedElement:
    return ExtractedElement(ElementType.HEADING, text, extra={"level": level})


def para(text: str, position: int | None = None) -> ExtractedElement:
    return ExtractedElement(ElementType.PARAGRAPH, text, position=position)


def table(text: str) -> ExtractedElement:
    return ExtractedElement(ElementType.TABLE, text)


def doc(*elements: ExtractedElement) -> ExtractedDocument:
    return ExtractedDocument(source_path="policy.docx", file_type="docx", elements=list(elements))


# --- token counting -----------------------------------------------------------


def test_heuristic_counter_counts_words_and_punctuation():
    assert COUNTER.count("Hello, world!") == 4  # hello , world !


# --- token chunker --------------------------------------------------------------


def test_token_chunker_respects_budget_and_overlaps():
    text = " ".join(f"word{i}" for i in range(1000))
    chunker = TokenChunker(max_tokens=300, overlap=50)
    pieces = chunker.split(text)
    assert len(pieces) == 4
    assert all(COUNTER.count(p) <= 300 for p in pieces)
    # The last 50 tokens of one window open the next.
    assert pieces[1].startswith("word250")


def test_token_chunker_short_text_is_single_piece():
    assert TokenChunker(max_tokens=100, overlap=10).split("short text") == ["short text"]


def test_token_chunker_rejects_bad_overlap():
    with pytest.raises(ValueError):
        TokenChunker(max_tokens=100, overlap=100)


# --- recursive chunker -----------------------------------------------------------


def test_recursive_splits_on_paragraphs_first():
    paragraphs = [HR_SENTENCE * 10 for _ in range(4)]  # ~160 tokens each
    text = "\n\n".join(paragraphs)
    pieces = RecursiveChunker(max_tokens=350).split(text)
    assert len(pieces) == 2  # two paragraphs merge per chunk
    assert all(COUNTER.count(p) <= 350 for p in pieces)


def test_recursive_merges_small_pieces_up_to_budget():
    text = "\n\n".join(["Tiny paragraph."] * 6)
    pieces = RecursiveChunker(max_tokens=100).split(text)
    assert len(pieces) == 1


def test_recursive_falls_through_to_sentences():
    text = " ".join([HR_SENTENCE.strip()] * 30)  # one huge paragraph, no \n
    pieces = RecursiveChunker(max_tokens=200).split(text)
    assert len(pieces) >= 2
    assert all(COUNTER.count(p) <= 200 for p in pieces)


# --- semantic chunker -------------------------------------------------------------


def test_headings_open_new_chunks_with_breadcrumbs():
    document = doc(
        heading("Employee Handbook", 1),
        para(HR_SENTENCE * 3),
        heading("Compensation", 2),
        para(FINANCE_SENTENCE * 3),
    )
    groups = SemanticChunker(max_tokens=512).group(document)
    assert len(groups) == 2
    assert groups[0].heading_path == ("Employee Handbook",)
    assert groups[1].heading_path == ("Employee Handbook", "Compensation")
    assert groups[1].text.startswith("Compensation")


def test_sibling_headings_replace_breadcrumb_level():
    document = doc(
        heading("Handbook", 1),
        heading("Leave", 2),
        para(HR_SENTENCE * 2),
        heading("Payroll", 2),
        para(FINANCE_SENTENCE * 2),
    )
    groups = SemanticChunker().group(document)
    assert groups[-1].heading_path == ("Handbook", "Payroll")


def test_tables_stay_whole_and_inherit_heading():
    document = doc(
        heading("Fee Schedule", 1),
        table("Plan | Cost\nBasic | 0\nPro | 99"),
    )
    groups = SemanticChunker().group(document)
    assert len(groups) == 1
    assert groups[0].keep_whole
    assert groups[0].element_types == ["heading", "table"]


def test_table_between_prose_becomes_own_group():
    document = doc(para(HR_SENTENCE), table("a | b"), para(HR_SENTENCE))
    groups = SemanticChunker().group(document)
    assert [g.keep_whole for g in groups] == [False, True, False]


def test_topic_shift_splits_prose():
    document = doc(
        para(HR_SENTENCE * 5),  # ~80 tokens of HR vocabulary
        para(FINANCE_SENTENCE * 5),  # disjoint finance vocabulary
    )
    chunker = SemanticChunker(max_tokens=1000, min_tokens=40)
    groups = chunker.group(document)
    assert len(groups) == 2


def test_cohesive_prose_stays_together():
    document = doc(para(HR_SENTENCE * 5), para(HR_SENTENCE * 5))
    groups = SemanticChunker(max_tokens=1000, min_tokens=40).group(document)
    assert len(groups) == 1


def test_lexical_cohesion_bounds():
    assert lexical_cohesion(HR_SENTENCE, HR_SENTENCE) == 1.0
    assert lexical_cohesion(HR_SENTENCE, FINANCE_SENTENCE) < 0.05


# --- generator ---------------------------------------------------------------------


def test_generator_enriches_chunks_with_provenance(tmp_path: Path, sample_docx: Path):
    from app.ingestion import IngestionPipeline

    result = IngestionPipeline(tmp_path / "v.json").ingest(sample_docx)
    chunks = ChunkGenerator(strategy="semantic").generate(result.document, result.metadata)

    assert chunks, "docx should produce at least one chunk"
    first = chunks[0]
    assert first.metadata["source"] == "report.docx"
    assert first.metadata["title"] == "Q3 Financial Report"
    assert first.metadata["strategy"] == "semantic"
    assert first.metadata["version"] == 1
    assert first.metadata["heading_path"] == ["Executive Summary"]
    assert any("table" in c.metadata["element_types"] for c in chunks)


def test_chunk_ids_are_deterministic_and_strategy_scoped():
    document = doc(heading("H", 1), para(HR_SENTENCE * 3))
    a = ChunkGenerator(strategy="semantic").generate(document)
    b = ChunkGenerator(strategy="semantic").generate(document)
    c = ChunkGenerator(strategy="recursive").generate(document)
    assert [x.id for x in a] == [y.id for y in b]
    assert a[0].id != c[0].id


def test_generator_rejects_unknown_strategy():
    with pytest.raises(ValueError, match="strategy"):
        ChunkGenerator(strategy="quantum")


def test_oversized_semantic_groups_fall_back_to_recursive():
    document = doc(heading("Policy", 1), para(HR_SENTENCE * 60))  # ~1000 tokens
    chunks = ChunkGenerator(strategy="semantic", max_tokens=300).generate(document)
    assert len(chunks) > 1
    assert all(ch.token_count <= 300 for ch in chunks)
    assert all(ch.metadata["heading_path"] == ["Policy"] for ch in chunks)


# --- validator ----------------------------------------------------------------------


def _chunk(text: str, index: int, **overrides) -> Chunk:
    meta = {"source": "s", "strategy": "semantic"} | overrides.pop("metadata", {})
    return Chunk(
        text=text,
        index=index,
        token_count=COUNTER.count(text),
        metadata=meta,
        **overrides,
    )


def test_validator_accepts_good_chunks():
    document = doc(para(HR_SENTENCE * 4), para(FINANCE_SENTENCE * 4))
    chunks = ChunkGenerator(strategy="semantic").generate(document)
    report = ChunkValidator().validate(chunks, document)
    assert report.ok, report.issues
    assert report.stats["coverage"] >= 0.99
    assert report.stats["chunks"] == len(chunks)


def test_validator_flags_oversized_unless_keep_whole():
    big = _chunk(HR_SENTENCE * 60, 0)
    report = ChunkValidator(max_tokens=300).validate([big])
    assert not report.ok and "exceeds limit" in report.issues[0]

    whole_table = _chunk(HR_SENTENCE * 60, 0, keep_whole=True)
    assert ChunkValidator(max_tokens=300).validate([whole_table]).ok


def test_validator_flags_empty_duplicate_and_gapped_chunks():
    chunks = [
        _chunk(HR_SENTENCE, 0),
        _chunk("   ", 1),
        _chunk(HR_SENTENCE, 3),  # duplicate text + index gap
    ]
    report = ChunkValidator(min_tokens=1).validate(chunks)
    issues = " ; ".join(report.issues)
    assert "empty text" in issues
    assert "duplicate of chunk 0" in issues
    assert "not contiguous" in issues


def test_validator_flags_missing_metadata_and_low_coverage():
    document = doc(para(HR_SENTENCE * 40))
    orphan = Chunk(text=HR_SENTENCE, index=0, token_count=COUNTER.count(HR_SENTENCE))
    report = ChunkValidator().validate([orphan], document)
    issues = " ; ".join(report.issues)
    assert "missing metadata 'source'" in issues
    assert "cover only" in issues


def test_validator_reports_empty_input():
    report = ChunkValidator().validate([])
    assert not report.ok


# --- end-to-end sanity across formats -------------------------------------------------


def test_full_pipeline_document_to_valid_chunks(sample_html: Path):
    document = extract(sample_html)
    chunks = ChunkGenerator(strategy="semantic", max_tokens=256).generate(document)
    report = ChunkValidator(max_tokens=256, min_tokens=2, min_coverage=0.5).validate(
        chunks, document
    )
    assert report.ok, report.issues
