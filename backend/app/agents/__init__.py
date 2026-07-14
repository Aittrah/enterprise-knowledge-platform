"""Multi-agent system: six domain agents, a router, and an orchestrator.

    from app.agents import AgentOrchestrator, ROSTER, OpenAICompatibleClient

    orchestrator = AgentOrchestrator(retriever, llm_client)
    answer = orchestrator.ask("How many leave days do I get?")
    answer.agent_id      # "hr" (routed)
    answer.text          # cited markdown answer
    answer.citations     # [{"n": 1, "source": "leave.pdf", "chunk_id": ...}]
"""

from app.agents.base import Agent, AgentAnswer, AgentProfile
from app.agents.llm import LLMClient, LLMReply, OpenAICompatibleClient
from app.agents.orchestrator import AgentOrchestrator
from app.agents.roster import ROSTER
from app.agents.router import AgentRouter

__all__ = [
    "Agent",
    "AgentAnswer",
    "AgentOrchestrator",
    "AgentProfile",
    "AgentRouter",
    "LLMClient",
    "LLMReply",
    "OpenAICompatibleClient",
    "ROSTER",
]
