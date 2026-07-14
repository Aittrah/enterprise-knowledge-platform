import { useEffect, useMemo, useState } from "react";
import { api, GraphViz } from "../lib/api";
import { EmptyState, PageHeader } from "../components/ui";

const TYPE_COLORS: Record<string, string> = {
  person: "#14a085",
  department: "#e37400",
  organization: "#8430ce",
  document: "#8f8b84",
  money: "#1e8e3e",
  date: "#b3540e",
  email: "#c2185b",
};

interface Placed {
  id: string;
  label: string;
  type: string;
  degree: number;
  x: number;
  y: number;
}

/** Deterministic force-ish layout: a few relaxation passes, no dependency. */
function layout(graph: GraphViz, width: number, height: number): Placed[] {
  const nodes: Placed[] = graph.nodes.map((node, index) => {
    const angle = (index / Math.max(1, graph.nodes.length)) * Math.PI * 2;
    const radius = Math.min(width, height) * 0.38;
    return {
      ...node,
      x: width / 2 + radius * Math.cos(angle),
      y: height / 2 + radius * Math.sin(angle),
    };
  });
  const byId = new Map(nodes.map((n) => [n.id, n]));
  for (let pass = 0; pass < 120; pass++) {
    // attraction along edges
    for (const edge of graph.edges) {
      const a = byId.get(edge.source);
      const b = byId.get(edge.target);
      if (!a || !b) continue;
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      a.x += dx * 0.02;
      a.y += dy * 0.02;
      b.x -= dx * 0.02;
      b.y -= dy * 0.02;
    }
    // pairwise repulsion
    for (const a of nodes) {
      for (const b of nodes) {
        if (a === b) continue;
        const dx = a.x - b.x;
        const dy = a.y - b.y;
        const distSq = Math.max(100, dx * dx + dy * dy);
        const force = 1800 / distSq;
        a.x += dx * force * 0.02;
        a.y += dy * force * 0.02;
      }
      a.x = Math.min(width - 40, Math.max(40, a.x));
      a.y = Math.min(height - 30, Math.max(30, a.y));
    }
  }
  return nodes;
}

export default function Graph() {
  const [graph, setGraph] = useState<GraphViz | null>(null);
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<string | null>(null);

  useEffect(() => {
    api.graphViz().then(setGraph).catch(() => {});
  }, []);

  const width = 900;
  const height = 560;
  const placed = useMemo(
    () => (graph ? layout(graph, width, height) : []),
    [graph],
  );
  const byId = useMemo(() => new Map(placed.map((n) => [n.id, n])), [placed]);

  const neighborIds = useMemo(() => {
    if (!graph || !selected) return new Set<string>();
    const ids = new Set<string>([selected]);
    for (const edge of graph.edges) {
      if (edge.source === selected) ids.add(edge.target);
      if (edge.target === selected) ids.add(edge.source);
    }
    return ids;
  }, [graph, selected]);

  const visible = query
    ? placed.filter((n) => n.label.toLowerCase().includes(query.toLowerCase()))
    : placed;
  const selectedEdges =
    graph?.edges.filter((e) => e.source === selected || e.target === selected) ?? [];

  return (
    <div className="pb-10">
      <PageHeader
        title="Knowledge Graph"
        sub="People, departments and documents your knowledge base connects. Click a node to inspect its evidence."
      />
      <div className="px-8 space-y-4">
        <input
          className="focusable w-72 bg-surface-1 border border-edge rounded-lg px-3.5 py-2 text-sm placeholder:text-ink-muted/60"
          placeholder="Search nodes…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        {!graph || graph.nodes.length === 0 ? (
          <EmptyState title="The graph builds itself as you upload documents." />
        ) : (
          <div className="grid xl:grid-cols-[1fr_320px] gap-4">
            <div className="card overflow-x-auto">
              <svg viewBox={`0 0 ${width} ${height}`} className="w-full min-w-[640px]">
                {graph.edges.map((edge, index) => {
                  const a = byId.get(edge.source);
                  const b = byId.get(edge.target);
                  if (!a || !b) return null;
                  const active =
                    selected && (edge.source === selected || edge.target === selected);
                  return (
                    <line
                      key={index}
                      x1={a.x}
                      y1={a.y}
                      x2={b.x}
                      y2={b.y}
                      stroke={active ? "var(--color-marginalia)" : "var(--color-edge)"}
                      strokeWidth={active ? 1.5 : 0.7}
                    />
                  );
                })}
                {visible.map((node) => {
                  const dimmed = selected && !neighborIds.has(node.id);
                  return (
                    <g
                      key={node.id}
                      transform={`translate(${node.x},${node.y})`}
                      opacity={dimmed ? 0.25 : 1}
                      className="cursor-pointer"
                      onClick={() =>
                        setSelected(selected === node.id ? null : node.id)
                      }
                    >
                      <circle
                        r={6 + Math.min(10, node.degree * 1.5)}
                        fill={TYPE_COLORS[node.type] ?? "#8f8b84"}
                        fillOpacity={0.85}
                        stroke={selected === node.id ? "var(--color-ink)" : "transparent"}
                        strokeWidth={2}
                      />
                      <text
                        y={-12 - Math.min(10, node.degree * 1.5)}
                        textAnchor="middle"
                        className="fill-ink text-[11px]"
                        style={{ fontFamily: "var(--font-mono)" }}
                      >
                        {node.label}
                      </text>
                    </g>
                  );
                })}
              </svg>
              <div className="px-4 py-3 border-t border-edge flex flex-wrap gap-4">
                {Object.entries(TYPE_COLORS).map(([type, color]) => (
                  <span key={type} className="text-[11px] font-mono text-ink-muted">
                    <span
                      className="inline-block w-2.5 h-2.5 rounded-full mr-1.5 align-middle"
                      style={{ background: color }}
                    />
                    {type}
                  </span>
                ))}
              </div>
            </div>
            <aside className="card p-5 h-fit">
              <h2 className="text-xs uppercase tracking-wider text-ink-muted mb-3">
                {selected ? byId.get(selected)?.label : "Evidence"}
              </h2>
              {!selected ? (
                <p className="text-sm text-ink-muted">
                  Select a node to see the relationships — and the exact
                  sentences — behind it.
                </p>
              ) : selectedEdges.length === 0 ? (
                <p className="text-sm text-ink-muted">No relationships recorded.</p>
              ) : (
                <ul className="space-y-3">
                  {selectedEdges.slice(0, 12).map((edge, index) => (
                    <li key={index} className="text-sm">
                      <div className="font-mono text-[11px] text-marginalia">
                        {edge.type}
                      </div>
                      <div className="text-ink-muted text-[13px] mt-0.5">
                        “{edge.evidence}”
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </aside>
          </div>
        )}
      </div>
    </div>
  );
}
