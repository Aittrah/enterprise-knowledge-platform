import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { AnalyticsSummary, api } from "../lib/api";
import { PageHeader, StatCard } from "../components/ui";

export default function Analytics() {
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);

  useEffect(() => {
    api.analytics().then(setSummary).catch(() => {});
    const timer = setInterval(
      () => api.analytics().then(setSummary).catch(() => {}),
      10000,
    );
    return () => clearInterval(timer);
  }, []);

  const agentData = summary
    ? Object.entries(summary.queries_by_agent).map(([agent, count]) => ({
        agent,
        queries: count,
      }))
    : [];
  const cache = summary?.embedding_cache;
  const cacheRate =
    cache && cache.hits + cache.misses > 0
      ? Math.round((cache.hits / (cache.hits + cache.misses)) * 100)
      : null;

  return (
    <div className="pb-10">
      <PageHeader title="Analytics" sub="Usage, cost signals and system health." />
      <div className="px-8 grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Queries" value={summary?.queries ?? "—"} />
        <StatCard
          label="Prompt tokens"
          value={summary?.prompt_tokens?.toLocaleString() ?? "—"}
        />
        <StatCard
          label="Completion tokens"
          value={summary?.completion_tokens?.toLocaleString() ?? "—"}
        />
        <StatCard
          label="Embedding cache"
          value={cacheRate === null ? "—" : `${cacheRate}%`}
          hint="hit rate — cached embeddings cost nothing"
        />
      </div>
      <div className="px-8 mt-6 grid lg:grid-cols-2 gap-4">
        <section className="card p-5">
          <h2 className="text-sm text-ink-muted uppercase tracking-wider mb-4">
            Queries by agent
          </h2>
          {agentData.length === 0 ? (
            <p className="text-sm text-ink-muted">No queries yet.</p>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={agentData}>
                <CartesianGrid stroke="#1a2438" vertical={false} />
                <XAxis
                  dataKey="agent"
                  stroke="#8a93a6"
                  fontSize={12}
                  tickLine={false}
                />
                <YAxis stroke="#8a93a6" fontSize={12} tickLine={false} allowDecimals={false} />
                <Tooltip
                  cursor={{ fill: "rgba(255,255,255,0.04)" }}
                  contentStyle={{
                    background: "#131b2c",
                    border: "1px solid rgba(255,255,255,0.1)",
                    borderRadius: 8,
                    color: "#e8ebea",
                  }}
                />
                <Bar dataKey="queries" fill="#2e9e83" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </section>
        <section className="card p-5">
          <h2 className="text-sm text-ink-muted uppercase tracking-wider mb-4">
            Knowledge base
          </h2>
          <dl className="grid grid-cols-2 gap-4 font-mono text-sm">
            <div>
              <dt className="text-[11px] text-ink-muted uppercase">Documents</dt>
              <dd className="text-xl mt-1">{summary?.documents ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-[11px] text-ink-muted uppercase">Chunks</dt>
              <dd className="text-xl mt-1">{summary?.chunks ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-[11px] text-ink-muted uppercase">Graph entities</dt>
              <dd className="text-xl mt-1">{summary?.graph.entities ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-[11px] text-ink-muted uppercase">Graph relations</dt>
              <dd className="text-xl mt-1">{summary?.graph.relations ?? "—"}</dd>
            </div>
          </dl>
          {summary && (
            <div className="mt-5 pt-4 border-t border-white/8 font-mono text-[12px] text-ink-muted space-y-1">
              <div>embedding: {summary.providers.embedding}</div>
              <div>llm: {summary.providers.llm}</div>
              <div>vector store: {summary.providers.vector_store}</div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
