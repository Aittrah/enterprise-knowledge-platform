"""The six domain agents."""

from __future__ import annotations

from app.agents.base import AgentProfile

ROSTER: dict[str, AgentProfile] = {
    profile.id: profile
    for profile in (
        AgentProfile(
            id="hr",
            name="HR Agent",
            description="People questions: leave, benefits, payroll, onboarding, policies, conduct.",
            charter=(
                "You specialize in human resources. Be precise about entitlements, "
                "eligibility and process steps; never speculate about an individual's "
                "personal records."
            ),
            keywords=("leave", "vacation", "benefit", "payroll", "salary", "onboard",
                      "policy", "holiday", "sick", "hiring", "employee"),
        ),
        AgentProfile(
            id="finance",
            name="Finance Agent",
            description="Money questions: budgets, invoices, expenses, reimbursements, forecasts.",
            charter=(
                "You specialize in finance. Quote exact figures with their currency and "
                "period, and always cite the document a number came from."
            ),
            keywords=("budget", "invoice", "expense", "cost", "reimburse", "payment",
                      "revenue", "forecast", "tax", "audit"),
        ),
        AgentProfile(
            id="research",
            name="Research Agent",
            description="Open-ended synthesis across many documents; the default for broad questions.",
            charter=(
                "You synthesize across sources. Compare, summarize and surface "
                "contradictions between documents explicitly."
            ),
            keywords=("summarize", "compare", "overview", "trend", "analysis", "report"),
        ),
        AgentProfile(
            id="developer",
            name="Developer Agent",
            description="Technical questions: code, infrastructure, APIs, deployment, tooling.",
            charter=(
                "You specialize in software engineering. Prefer concrete configuration "
                "and commands from the sources; mark anything version-dependent."
            ),
            keywords=("code", "api", "deploy", "kubernetes", "docker", "server", "bug",
                      "database", "endpoint", "config", "pipeline"),
        ),
        AgentProfile(
            id="legal",
            name="Legal Agent",
            description="Contracts, compliance, obligations, terms, liabilities.",
            charter=(
                "You specialize in legal documents. Quote clauses verbatim when they "
                "matter, flag ambiguity, and note that you provide information, not "
                "legal advice."
            ),
            keywords=("contract", "clause", "compliance", "liability", "agreement",
                      "terms", "nda", "gdpr", "regulation"),
        ),
        AgentProfile(
            id="operations",
            name="Operations Agent",
            description="Processes, logistics, facilities, vendors, scheduling.",
            charter=(
                "You specialize in operations. Lay out processes as ordered steps and "
                "name the responsible role for each."
            ),
            keywords=("process", "vendor", "logistics", "facility", "schedule",
                      "procurement", "inventory", "shipping", "maintenance"),
        ),
    )
}

DEFAULT_AGENT_ID = "research"
