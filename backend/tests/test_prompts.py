import pytest

from app.prompts import (
    PROMPTS,
    PromptTemplate,
    TemplateError,
    extract_json,
    format_context,
    format_graph_context,
    json_output_rules,
    parse_citations,
    verify_citations,
)
from app.prompts.templates import escape_braces
from app.retrieval.base import RetrievedChunk


def chunk(cid: str, text: str, **metadata) -> RetrievedChunk:
    return RetrievedChunk(id=cid, text=text, score=0.9, metadata=metadata)


# --- templates ------------------------------------------------------------------


def test_template_renders_system_and_user_messages():
    template = PromptTemplate(name="t", system="You are {name}.", user="Q: {q}")
    messages = template.render(name="EKIP", q="hi")
    assert messages == [
        {"role": "system", "content": "You are EKIP."},
        {"role": "user", "content": "Q: hi"},
    ]


def test_template_missing_variable_raises():
    template = PromptTemplate(name="t", system="{a}", user="{b}")
    with pytest.raises(TemplateError, match="missing.*'b'"):
        template.render(a="x")


def test_template_unknown_variable_raises():
    template = PromptTemplate(name="t", system="hello", user="{a}")
    with pytest.raises(TemplateError, match="unknown.*'oops'"):
        template.render(a="x", oops="y")


def test_escape_braces_makes_user_text_safe():
    template = PromptTemplate(name="t", system="s", user="{payload}")
    rendered = template.render(payload=escape_braces("code {block} here"))
    assert "{block}" in rendered[1]["content"].replace("{{", "{").replace("}}", "}")


def test_library_templates_declare_expected_variables():
    assert PROMPTS["rag_answer"].variables == {
        "agent_name",
        "agent_charter",
        "context",
        "graph_context",
        "question",
    }
    assert "question" in PROMPTS["router"].variables


# --- context formatting -------------------------------------------------------------


def test_format_context_numbers_blocks_and_maps_citations():
    chunks = [
        chunk("a", "First passage.", source="leave.pdf", heading_path=["Handbook", "Leave"], pages=[4]),
        chunk("b", "Second passage.", source="budget.xlsx"),
    ]
    text, citation_map = format_context(chunks)
    assert "[1] leave.pdf (section: Handbook > Leave, pages: 4)" in text
    assert "[2] budget.xlsx" in text
    assert text.index("[1]") < text.index("[2]")
    assert citation_map[1].id == "a" and citation_map[2].id == "b"


def test_format_graph_context_renders_evidence():
    rendered = format_graph_context(
        [
            {
                "source": "person:sara khan",
                "target": "department:finance",
                "type": "WORKS_IN",
                "evidence": "Sara Khan works in the Finance department.",
            }
        ]
    )
    assert "sara khan —WORKS_IN→ finance" in rendered
    assert "Sara Khan works in the Finance department." in rendered
    assert format_graph_context([]) == ""


# --- citations -----------------------------------------------------------------------


def test_parse_citations_unique_in_first_appearance_order():
    assert parse_citations("Leave is 22 days [2][1], carried over [2].") == [2, 1]
    assert parse_citations("no citations here") == []


def test_verify_citations_flags_invented_numbers():
    assert verify_citations("fact [1], fake [7]", available={1, 2, 3}) == [7]
    assert verify_citations("fact [1][2]", available={1, 2}) == []


# --- structured output ------------------------------------------------------------------


def test_json_rules_embed_schema():
    rules = json_output_rules({"type": "object", "properties": {"x": {"type": "string"}}})
    assert '"properties"' in rules and "single JSON object" in rules


@pytest.mark.parametrize(
    "reply",
    [
        '{"answer": 42}',
        'Sure! Here you go:\n```json\n{"answer": 42}\n```',
        'The result is {"answer": 42} as requested.',
    ],
)
def test_extract_json_tolerates_model_formatting(reply):
    assert extract_json(reply) == {"answer": 42}


def test_extract_json_raises_on_garbage():
    with pytest.raises(ValueError, match="no parseable JSON"):
        extract_json("I cannot answer that.")
