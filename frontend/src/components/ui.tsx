import type { ReactNode } from "react";

export function PageHeader({ title, sub }: { title: string; sub?: string }) {
  return (
    <header className="px-8 pt-8 pb-4">
      <h1 className="font-display text-3xl">{title}</h1>
      {sub && <p className="text-ink-muted text-sm mt-1">{sub}</p>}
    </header>
  );
}

export function StatCard({
  label,
  value,
  hint,
}: {
  label: string;
  value: string | number;
  hint?: string;
}) {
  return (
    <div className="card p-5">
      <div className="text-xs text-ink-muted uppercase tracking-wider">{label}</div>
      <div className="font-mono text-2xl mt-2">{value}</div>
      {hint && <div className="text-xs text-ink-muted mt-1">{hint}</div>}
    </div>
  );
}

export function EmptyState({
  title,
  action,
}: {
  title: string;
  action?: ReactNode;
}) {
  return (
    <div className="card p-10 text-center">
      <div className="font-display text-xl text-ink-muted">{title}</div>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

/** Groundedness seal — the signature confidence mark (Module 21). */
export function Seal({ grounded }: { grounded: boolean }) {
  return (
    <span
      title={grounded ? "Grounded: every citation verified" : "Unverified answer"}
      className={`inline-flex items-center gap-1.5 text-[11px] font-mono px-2 py-0.5 rounded-full border ${
        grounded
          ? "text-verdigris-bright border-verdigris/40 bg-verdigris/10"
          : "text-marginalia border-marginalia/40 bg-marginalia/10"
      }`}
    >
      ◉ {grounded ? "grounded" : "unverified"}
    </span>
  );
}

/** Minimal safe markdown-ish rendering: bold, inline code, citation tags. */
export function AnswerText({ text }: { text: string }) {
  const parts = text.split(/(\[\d+\]|\*\*[^*]+\*\*|`[^`]+`)/g);
  return (
    <div className="whitespace-pre-wrap leading-relaxed text-[15px]">
      {parts.map((part, i) => {
        if (/^\[\d+\]$/.test(part)) {
          return (
            <span
              key={i}
              className="font-mono text-[12px] text-marginalia border-b border-marginalia/60 mx-0.5"
            >
              {part}
            </span>
          );
        }
        if (/^\*\*[^*]+\*\*$/.test(part)) {
          return <strong key={i}>{part.slice(2, -2)}</strong>;
        }
        if (/^`[^`]+`$/.test(part)) {
          return (
            <code key={i} className="font-mono text-[13px] bg-surface-2 px-1 rounded">
              {part.slice(1, -1)}
            </code>
          );
        }
        return <span key={i}>{part}</span>;
      })}
    </div>
  );
}
