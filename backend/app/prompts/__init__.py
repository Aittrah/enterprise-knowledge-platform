"""Prompt library: templates, context formatting, citations, structured output.

    from app.prompts import PROMPTS, format_context, parse_citations

    context, citation_map = format_context(result.chunks)
    messages = PROMPTS["rag_answer"].render(context=context, question=query)
    ...
    cited = parse_citations(answer_text)   # -> [1, 3]
"""

from app.prompts.citations import CITATION_RULES, parse_citations, verify_citations
from app.prompts.context import format_context, format_graph_context
from app.prompts.library import PROMPTS
from app.prompts.structured import extract_json, json_output_rules
from app.prompts.templates import PromptTemplate, TemplateError

__all__ = [
    "CITATION_RULES",
    "PROMPTS",
    "PromptTemplate",
    "TemplateError",
    "extract_json",
    "format_context",
    "format_graph_context",
    "json_output_rules",
    "parse_citations",
    "verify_citations",
]
