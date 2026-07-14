"""Route a question to the best domain agent.

Keyword scoring is the always-available baseline; an LLM router can be
layered on and falls back to keywords whenever it errs or answers with an
unknown id — routing must never be the reason a question fails.
"""

from __future__ import annotations

import re

from app.agents.base import AgentProfile
from app.agents.llm import LLMClient
from app.agents.roster import DEFAULT_AGENT_ID, ROSTER
from app.prompts import PROMPTS

_WORDS = re.compile(r"[a-z][\w-]*")


class AgentRouter:
    def __init__(
        self,
        roster: dict[str, AgentProfile] | None = None,
        llm: LLMClient | None = None,
        default_id: str = DEFAULT_AGENT_ID,
    ) -> None:
        self._roster = roster or ROSTER
        self._llm = llm
        self._default_id = default_id

    def route(self, question: str) -> AgentProfile:
        if self._llm is not None:
            profile = self._route_with_llm(question)
            if profile is not None:
                return profile
        return self._route_with_keywords(question)

    def _route_with_keywords(self, question: str) -> AgentProfile:
        words = set(_WORDS.findall(question.lower()))
        best_id, best_score = self._default_id, 0
        for agent_id, profile in self._roster.items():
            score = sum(1 for kw in profile.keywords if kw in words)
            if score > best_score:
                best_id, best_score = agent_id, score
        return self._roster[best_id]

    def _route_with_llm(self, question: str) -> AgentProfile | None:
        agents = "\n".join(
            f"- {p.id}: {p.description}" for p in self._roster.values()
        )
        try:
            reply = self._llm.chat(
                PROMPTS["router"].render(agents=agents, question=question),
                temperature=0.0,
            )
        except Exception:
            return None
        candidate = reply.text.strip().strip('"').lower()
        return self._roster.get(candidate)
