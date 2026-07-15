"""Agent: a persona + retrieval scope that produces cited answers."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.agents.llm import LLMClient
from app.prompts import PROMPTS, format_context, format_graph_context, verify_citations
from app.prompts.templates import escape_braces
from app.retrieval.base import RetrievedChunk, Retriever
from app.stores.base import Filters


@dataclass(frozen=True)
class AgentProfile:
    id: str
    name: str
    description: str  # shown to the router and the UI agent picker
    charter: str  # persona + domain instructions injected into the prompt
    keywords: tuple[str, ...] = ()
    filters: Filters | None = None  # optional retrieval scope (tags, sources)


@dataclass
class AgentAnswer:
    agent_id: str
    question: str
    text: str
    chunks: list[RetrievedChunk] = field(default_factory=list)
    citations: list[dict] = field(default_factory=list)
    invalid_citations: list[int] = field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    retrieval_ms: float = 0.0
    # Attached by the guardrail layer (M20) after generation.
    guardrail: dict | None = None

    @property
    def grounded(self) -> bool:
        """Cited at least once and invented nothing."""
        return bool(self.citations) and not self.invalid_citations


class Agent:
    def __init__(self, profile: AgentProfile) -> None:
        self.profile = profile

    def answer(
        self,
        question: str,
        retriever: Retriever,
        llm: LLMClient,
        top_k: int = 6,
    ) -> AgentAnswer:
        result = retriever.retrieve(question, top_k=top_k, filters=self.profile.filters)
        context, citation_map = format_context(result.chunks)
        graph_context = format_graph_context(result.debug.get("graph_context", []))

        messages = PROMPTS["rag_answer"].render(
            agent_name=self.profile.name,
            agent_charter=escape_braces(self.profile.charter),
            context=escape_braces(context) if context else "(no sources found)",
            graph_context=escape_braces(graph_context),
            question=escape_braces(question),
        )
        reply = llm.chat(messages)

        invalid = verify_citations(reply.text, set(citation_map))
        citations = [
            {
                "n": number,
                "source": chunk.source,
                "chunk_id": chunk.id,
                "heading_path": chunk.metadata.get("heading_path", []),
                "score": chunk.score,
                "excerpt": chunk.text[:220],
            }
            for number, chunk in citation_map.items()
            if number in set(_cited(reply.text))
        ]
        return AgentAnswer(
            agent_id=self.profile.id,
            question=question,
            text=reply.text,
            chunks=result.chunks,
            citations=citations,
            invalid_citations=invalid,
            prompt_tokens=reply.prompt_tokens,
            completion_tokens=reply.completion_tokens,
            retrieval_ms=result.elapsed_ms,
        )


def _cited(text: str) -> list[int]:
    from app.prompts import parse_citations

    return parse_citations(text)
