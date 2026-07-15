/** Animated answer-details tree: expands to show how the answer was made —
 *  agent → groundedness → each citation → source, section, score, excerpt.
 *  Branches slide in staggered; the whole tree folds closed smoothly. */

import { useState } from "react";
import type { Citation } from "../lib/api";
import { FileIcon } from "./FileIcon";

function Node({
  index,
  label,
  children,
  defaultOpen = false,
}: {
  index: number;
  label: React.ReactNode;
  children?: React.ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const expandable = children !== undefined;
  return (
    <div className="tree-node" style={{ "--i": index } as React.CSSProperties}>
      <button
        type="button"
        className={`focusable flex items-center gap-1.5 py-1 text-[13px] ${
          expandable ? "hover:text-ink text-ink-muted" : "text-ink-muted cursor-default"
        }`}
        onClick={() => expandable && setOpen(!open)}
        aria-expanded={expandable ? open : undefined}
      >
        {expandable ? (
          <span className="chevron font-mono text-[10px]" data-open={open} aria-hidden>
            ▶
          </span>
        ) : (
          <span className="font-mono text-[10px] opacity-50" aria-hidden>
            ─
          </span>
        )}
        {label}
      </button>
      {expandable && (
        <div className="tree-expand" data-open={open}>
          <div>
            <div className="tree-branch">{open && children}</div>
          </div>
        </div>
      )}
    </div>
  );
}

export function DetailsTree({
  agentId,
  grounded,
  citations,
}: {
  agentId?: string;
  grounded?: boolean;
  citations: Citation[];
}) {
  return (
    <div className="mt-1 font-sans">
      <Node
        index={0}
        defaultOpen
        label={<span className="font-mono text-[11px] uppercase tracking-wider">answer details</span>}
      >
        <Node
          index={0}
          label={
            <span>
              agent · <span className="text-ink font-medium">{agentId ?? "auto"}</span>
            </span>
          }
        />
        <Node
          index={1}
          label={
            <span>
              groundedness ·{" "}
              <span className={grounded ? "text-verdigris" : "text-marginalia"}>
                {grounded ? "verified" : "unverified"}
              </span>
            </span>
          }
        />
        <Node
          index={2}
          label={
            <span>
              sources · <span className="text-ink font-medium">{citations.length}</span>
            </span>
          }
        >
          {citations.map((citation, i) => (
            <Node
              index={i}
              key={citation.n}
              label={
                <span className="flex items-center gap-2">
                  <span className="font-mono text-[11px] text-marginalia">[{citation.n}]</span>
                  <FileIcon type={citation.source} size={13} />
                  <span className="text-ink">{citation.source}</span>
                </span>
              }
            >
              {citation.heading_path.length > 0 && (
                <Node
                  index={0}
                  label={<span>section · {citation.heading_path.join(" › ")}</span>}
                />
              )}
              <Node
                index={1}
                label={
                  <span className="flex items-center gap-2">
                    match
                    <span className="inline-block h-1.5 w-24 rounded-full bg-surface-2 overflow-hidden">
                      <span
                        className="score-bar block h-full rounded-full bg-ink"
                        style={{ width: `${Math.round(citation.score * 100)}%` }}
                      />
                    </span>
                    <span className="font-mono text-[11px]">
                      {Math.round(citation.score * 100)}%
                    </span>
                  </span>
                }
              />
              {citation.excerpt && (
                <div
                  className="tree-node py-1.5 pr-2 text-[12px] leading-relaxed text-ink-muted italic"
                  style={{ "--i": 2 } as React.CSSProperties}
                >
                  “{citation.excerpt}…”
                </div>
              )}
            </Node>
          ))}
        </Node>
      </Node>
    </div>
  );
}
