from pathlib import Path

from app.ingestion import IngestionPipeline
from app.ingestion.models import ElementType, ExtractedDocument, ExtractedElement
from app.processing import CleaningPipeline, DeduplicationEngine, normalize_text
from app.processing.dedup import estimate_similarity, minhash_signature
from app.processing.headers_footers import strip_headers_footers


def para(text: str, position: int | None = None) -> ExtractedElement:
    return ExtractedElement(ElementType.PARAGRAPH, text, position=position)


def doc(*elements: ExtractedElement) -> ExtractedDocument:
    return ExtractedDocument(source_path="x", file_type="test", elements=list(elements))


# --- normalization -----------------------------------------------------------


def test_normalize_folds_ligatures_quotes_and_dashes():
    assert normalize_text("ﬁnancial “report” — draft") == 'financial "report" - draft'


def test_normalize_repairs_linebreak_hyphenation():
    assert normalize_text("compre-\nhensive infor-\nmation") == "comprehensive information"


def test_normalize_strips_control_chars_and_collapses_whitespace():
    assert normalize_text("a\x00b\x0c  c\t\td\n\n\n\n\ne") == "ab c d\n\ne"


def test_normalize_is_idempotent():
    once = normalize_text("ﬁx  “this”­ text…")
    assert normalize_text(once) == once


# --- header / footer removal -------------------------------------------------


def _paged_document() -> ExtractedDocument:
    topics = ["hiring", "expenses", "security", "travel"]
    pages = []
    for n, topic in enumerate(topics, start=1):
        pages.append(
            para(
                f"ACME Corp - Confidential\nThis section covers the {topic} policy.\n"
                f"Detailed rules for {topic} follow below.\nPage {n} of 4",
                position=n,
            )
        )
    return doc(*pages)


def test_repeated_headers_and_footers_are_stripped():
    document = _paged_document()
    removed = strip_headers_footers(document)
    assert removed == 8  # header + footer on each of 4 pages
    assert "ACME Corp" not in document.text
    assert "Page 2 of 4" not in document.text
    assert "This section covers the expenses policy." in document.text


def test_short_documents_are_left_alone():
    document = doc(
        para("ACME Corp - Confidential\nBody one.", position=1),
        para("ACME Corp - Confidential\nBody two.", position=2),
    )
    assert strip_headers_footers(document) == 0
    assert "ACME Corp" in document.text


def test_unpaginated_documents_are_left_alone():
    document = doc(para("ACME Corp - Confidential"), para("Body."))
    assert strip_headers_footers(document) == 0


# --- deduplication engine ------------------------------------------------------


POLICY = (
    "Employees are entitled to twenty two days of paid annual leave per "
    "calendar year, accrued monthly and subject to manager approval."
)


def test_exact_duplicates_detected_despite_formatting():
    engine = DeduplicationEngine()
    engine.add("a", POLICY)
    match = engine.check("  " + POLICY.upper() + "\n")
    assert match is not None and match.kind == "exact" and match.original_key == "a"


def test_near_duplicates_detected():
    engine = DeduplicationEngine(near_threshold=0.7)
    engine.add("a", POLICY)
    tweaked = POLICY.replace("manager approval", "supervisor approval")
    match = engine.check(tweaked)
    assert match is not None and match.kind == "near"
    assert 0.7 <= match.similarity < 1.0


def test_distinct_texts_do_not_match():
    engine = DeduplicationEngine()
    engine.add("a", POLICY)
    assert engine.check("Quarterly revenue grew fourteen percent year over year.") is None


def test_minhash_estimates_track_overlap():
    sig_a = minhash_signature(POLICY)
    assert estimate_similarity(sig_a, minhash_signature(POLICY)) == 1.0
    disjoint = minhash_signature("totally unrelated words about container orchestration")
    assert estimate_similarity(sig_a, disjoint) < 0.2


# --- cleaning pipeline ---------------------------------------------------------


def test_cleaning_pipeline_end_to_end():
    document = doc(
        para("ﬁrst “paragraph” with  artifacts", position=1),
        para("Page 1 of 9", position=1),
        para(POLICY, position=1),
        para(POLICY, position=2),  # exact duplicate
        para(POLICY.replace("manager approval", "supervisor approval"), position=2),
    )
    stats = CleaningPipeline(near_threshold=0.7).clean(document)

    assert stats.elements_in == 5
    assert stats.boilerplate_dropped == 1
    assert stats.exact_duplicates_dropped == 1
    assert stats.near_duplicates_dropped == 1
    assert stats.elements_out == 2
    assert document.text.startswith('first "paragraph"')
    assert document.native_properties["cleaning"]["elements_out"] == 2


def test_structured_rows_are_never_near_deduped():
    row_a = ExtractedElement(ElementType.ROW, "id: 1 | vendor: Acme Corp | amount: 100.00")
    row_b = ExtractedElement(ElementType.ROW, "id: 2 | vendor: Acme Corp | amount: 100.00")
    document = doc(row_a, row_b)
    stats = CleaningPipeline(near_threshold=0.5).clean(document)
    assert stats.near_duplicates_dropped == 0
    assert stats.elements_out == 2


def test_ingestion_pipeline_cleans_by_default(tmp_path: Path):
    messy = tmp_path / "messy.txt"
    messy.write_text("ﬁnancial “summary”\n\nPage 1 of 2\n\nReal content here.", encoding="utf-8")
    result = IngestionPipeline(tmp_path / "v.json").ingest(messy)
    assert 'financial "summary"' in result.document.text
    assert "Page 1 of 2" not in result.document.text
    assert result.document.native_properties["cleaning"]["boilerplate_dropped"] == 1


def test_ingestion_pipeline_clean_can_be_disabled(tmp_path: Path):
    messy = tmp_path / "messy.txt"
    messy.write_text("ﬁnancial “summary”", encoding="utf-8")
    result = IngestionPipeline(tmp_path / "v.json", clean=False).ingest(messy)
    assert "ﬁnancial" in result.document.text
