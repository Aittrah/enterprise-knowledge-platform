"""AgentOrchestrator: the single entry point of the AI layer.

route (unless the user pinned an agent) -> retrieve -> prompt -> LLM ->
verified, cited AgentAnswer.
"""

from __future__ import annotations

from app.agents.base import Agent, AgentAnswer, AgentProfile
from app.agents.llm import LLMClient
from app.agents.roster import ROSTER
from app.agents.router import AgentRouter
from app.retrieval.base import Retriever


class AgentOrchestrator:
    def __init__(
        self,
        retriever: Retriever,
        llm: LLMClient,
        roster: dict[str, AgentProfile] | None = None,
        router: AgentRouter | None = None,
    ) -> None:
        self._retriever = retriever
        self._llm = llm
        self._roster = roster or ROSTER
        self._router = router or AgentRouter(roster=self._roster)

    @property
    def agents(self) -> list[AgentProfile]:
        return list(self._roster.values())

    def ask(
        self, question: str, agent_id: str | None = None, top_k: int = 6
    ) -> AgentAnswer:
        if agent_id is not None:
            try:
                profile = self._roster[agent_id]
            except KeyError:
                raise ValueError(
                    f"unknown agent '{agent_id}'; available: {sorted(self._roster)}"
                ) from None
        else:
            profile = self._router.route(question)
        return Agent(profile).answer(question, self._retriever, self._llm, top_k=top_k)
