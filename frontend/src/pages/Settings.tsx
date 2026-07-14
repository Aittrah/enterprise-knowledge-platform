import { useEffect, useState } from "react";
import { AnalyticsSummary, api } from "../lib/api";
import { PageHeader } from "../components/ui";
import { useSession } from "../stores/session";

export default function Settings() {
  const user = useSession((s) => s.user);
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);

  useEffect(() => {
    api.analytics().then(setSummary).catch(() => {});
  }, []);

  return (
    <div className="pb-10">
      <PageHeader title="Settings" sub="Profile and platform configuration." />
      <div className="px-8 grid lg:grid-cols-2 gap-4 max-w-4xl">
        <section className="card p-5">
          <h2 className="text-sm text-ink-muted uppercase tracking-wider mb-4">Profile</h2>
          <dl className="space-y-3 text-sm">
            <div>
              <dt className="text-[11px] text-ink-muted uppercase">Name</dt>
              <dd className="mt-0.5">{user?.name}</dd>
            </div>
            <div>
              <dt className="text-[11px] text-ink-muted uppercase">Email</dt>
              <dd className="mt-0.5 font-mono text-[13px]">{user?.email}</dd>
            </div>
            <div>
              <dt className="text-[11px] text-ink-muted uppercase">Role</dt>
              <dd className="mt-0.5 font-mono text-[13px]">{user?.role}</dd>
            </div>
          </dl>
        </section>
        <section className="card p-5">
          <h2 className="text-sm text-ink-muted uppercase tracking-wider mb-4">
            Active providers
          </h2>
          {summary ? (
            <dl className="space-y-3 text-sm">
              <div>
                <dt className="text-[11px] text-ink-muted uppercase">LLM</dt>
                <dd className="mt-0.5 font-mono text-[13px]">{summary.providers.llm}</dd>
              </div>
              <div>
                <dt className="text-[11px] text-ink-muted uppercase">Embedding model</dt>
                <dd className="mt-0.5 font-mono text-[13px]">
                  {summary.providers.embedding}
                </dd>
              </div>
              <div>
                <dt className="text-[11px] text-ink-muted uppercase">Vector store</dt>
                <dd className="mt-0.5 font-mono text-[13px]">
                  {summary.providers.vector_store}
                </dd>
              </div>
            </dl>
          ) : (
            <p className="text-sm text-ink-muted">Loading…</p>
          )}
          <p className="text-[12px] text-ink-muted mt-5 pt-4 border-t border-white/8 leading-relaxed">
            Providers are configured through the backend environment
            (<span className="font-mono">.env</span>): set{" "}
            <span className="font-mono">OPENAI_API_KEY</span> for synthesized
            answers, <span className="font-mono">EMBEDDING_PROVIDER</span> and{" "}
            <span className="font-mono">VECTOR_STORE=qdrant</span> for the
            production stack. In-app provider switching arrives with the Admin
            dashboard (Module 21).
          </p>
        </section>
      </div>
    </div>
  );
}
