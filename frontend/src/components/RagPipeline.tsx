import { useEffect, useRef, useState } from "react";

type Stage = {
  key: string;
  icon: string;
  label: string;
  sub: string;
  detail: string;
};

const STAGES: Stage[] = [
  {
    key: "query",
    icon: "🔎",
    label: "Query",
    sub: "user asks",
    detail: 'user: "how does our refund policy handle partial returns?"',
  },
  {
    key: "embed",
    icon: "🧬",
    label: "Embed",
    sub: "vectorize",
    detail: "text-embedding-3-small · 1536-dim vector · cache miss",
  },
  {
    key: "retrieve",
    icon: "📚",
    label: "Retrieve",
    sub: "top-k chunks",
    detail: "vector search → 8 candidate chunks from 3 documents",
  },
  {
    key: "rerank",
    icon: "🎯",
    label: "Rerank",
    sub: "score & filter",
    detail: "cross-encoder rerank → 4 chunks kept · confidence 0.87",
  },
  {
    key: "llm",
    icon: "🧠",
    label: "LLM",
    sub: "grounded answer",
    detail: "claude-sonnet-5 · grounded synthesis with 4 citations",
  },
  {
    key: "cite",
    icon: "📎",
    label: "Cite",
    sub: "with sources",
    detail: "[refund-policy.md#p3] [returns-faq.pdf#p1] [ops-runbook.md#p12]",
  },
];

export default function RagPipeline() {
  const [active, setActive] = useState(0);
  const [inView, setInView] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(
      ([e]) => setInView(e.isIntersecting),
      { threshold: 0.2 }
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);

  useEffect(() => {
    if (!inView) return;
    const id = setInterval(() => {
      setActive((i) => (i + 1) % STAGES.length);
    }, 1800);
    return () => clearInterval(id);
  }, [inView]);

  const current = STAGES[active];

  return (
    <section ref={ref} className="card p-6 relative overflow-hidden">
      <div className="flex items-baseline justify-between mb-5">
        <div>
          <h2 className="text-sm text-ink-muted uppercase tracking-wider">
            Live RAG Pipeline
          </h2>
          <p className="text-xs text-ink-muted mt-1">
            how EKIP answers every question — retrieval-augmented, grounded, cited.
          </p>
        </div>
        <span className="flex items-center gap-1.5 text-[11px] text-verdigris uppercase tracking-widest">
          <span className="rag-live-dot" />
          streaming
        </span>
      </div>

      {/* stages row */}
      <div className="rag-pipeline">
        {STAGES.map((stage, idx) => {
          const isActive = idx === active;
          const isDone = idx < active;
          return (
            <div key={stage.key} className="rag-stage-wrap">
              <button
                type="button"
                onClick={() => setActive(idx)}
                className={`rag-stage ${isActive ? "active" : ""} ${
                  isDone ? "done" : ""
                }`}
                aria-label={stage.label}
              >
                <span className="rag-stage-icon">{stage.icon}</span>
                <span className="rag-stage-label">{stage.label}</span>
                <span className="rag-stage-sub">{stage.sub}</span>
                {isActive && <span className="rag-stage-ping" />}
              </button>
              {idx < STAGES.length - 1 && (
                <div className={`rag-connector ${idx < active ? "flowed" : ""}`}>
                  <span className="rag-particle" />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* readout */}
      <div key={active} className="rag-readout">
        <span className="rag-readout-tag">
          {current.icon} {current.label.toUpperCase()}
        </span>
        <code className="rag-readout-line">{current.detail}</code>
      </div>
    </section>
  );
}
