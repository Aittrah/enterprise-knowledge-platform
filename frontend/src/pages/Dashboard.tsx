import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { AnalyticsSummary, api } from "../lib/api";
import { PageHeader, StatCard } from "../components/ui";
import { useSession } from "../stores/session";

export default function Dashboard() {
  const user = useSession((s) => s.user);
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [conversations, setConversations] = useState<string[]>([]);

  useEffect(() => {
    api.analytics().then(setSummary).catch(() => {});
    api.conversations().then(setConversations).catch(() => {});
  }, []);

  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";

  return (
    <div className="pb-10">
      <PageHeader
        title={`${greeting}, ${user?.name?.split(" ")[0] ?? "there"}`}
        sub="Your knowledge base at a glance."
      />
      <div className="px-8 grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Documents" value={summary?.documents ?? "—"} />
        <StatCard label="Indexed chunks" value={summary?.chunks ?? "—"} />
        <StatCard label="Queries" value={summary?.queries ?? "—"} />
        <StatCard
          label="Tokens used"
          value={summary ? summary.prompt_tokens + summary.completion_tokens : "—"}
          hint={summary ? `LLM: ${summary.providers.llm}` : undefined}
        />
      </div>
      <div className="px-8 mt-6 grid lg:grid-cols-2 gap-4">
        <section className="card p-5">
          <h2 className="text-sm text-ink-muted uppercase tracking-wider mb-4">
            Recent conversations
          </h2>
          {conversations.length === 0 ? (
            <p className="text-ink-muted text-sm">
              None yet —{" "}
              <Link to="/chat" className="focusable text-verdigris-bright">
                start your first chat
              </Link>
              .
            </p>
          ) : (
            <ul className="space-y-2">
              {conversations.slice(0, 6).map((id) => (
                <li key={id}>
                  <Link
                    to={`/chat?c=${id}`}
                    className="focusable font-mono text-sm text-ink-muted hover:text-ink"
                  >
                    ▸ conversation {id}
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>
        <section className="card p-5">
          <h2 className="text-sm text-ink-muted uppercase tracking-wider mb-4">
            Quick actions
          </h2>
          <div className="flex flex-wrap gap-3">
            <Link
              to="/knowledge"
              className="focusable bg-verdigris hover:bg-verdigris-bright text-surface-0 text-sm font-medium rounded-lg px-4 py-2.5 transition-colors"
            >
              Upload documents
            </Link>
            <Link
              to="/chat"
              className="focusable border border-white/10 hover:border-verdigris/50 text-sm rounded-lg px-4 py-2.5 transition-colors"
            >
              Ask a question
            </Link>
            <Link
              to="/graph"
              className="focusable border border-white/10 hover:border-verdigris/50 text-sm rounded-lg px-4 py-2.5 transition-colors"
            >
              Explore the graph
            </Link>
          </div>
          {summary && (
            <div className="mt-5 font-mono text-[12px] text-ink-muted space-y-1">
              <div>graph: {summary.graph.entities} entities · {summary.graph.relations} relations</div>
              <div>
                embedding cache: {summary.embedding_cache.hits} hits ·{" "}
                {summary.embedding_cache.misses} misses
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
