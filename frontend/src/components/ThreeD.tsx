/** Spline-style monochrome 3D moments, in pure CSS transforms.
 *  DominoCascade — the login hero, echoing the reference video's slabs.
 *  Chunking3D   — a document splitting into layers while indexing. */

export function DominoCascade() {
  const slabs = Array.from({ length: 9 });
  return (
    <div className="scene relative h-56 w-full overflow-visible" aria-hidden>
      <div className="orb absolute -top-4 right-8 h-24 w-24 rounded-full opacity-70" />
      <div className="preserve-3d relative h-full">
        {slabs.map((_, i) => (
          <div
            key={i}
            className="domino absolute rounded-[3px]"
            style={
              {
                "--i": i,
                left: `${8 + i * 9.5}%`,
                top: `${52 - Math.sin((i / (slabs.length - 1)) * Math.PI) * 26}%`,
                width: "26px",
                height: "72px",
                background:
                  "linear-gradient(160deg, var(--color-ink) 0%, color-mix(in srgb, var(--color-ink) 62%, var(--color-surface-0)) 100%)",
              } as React.CSSProperties
            }
          />
        ))}
      </div>
    </div>
  );
}

export function Chunking3D({ size = 44 }: { size?: number }) {
  const layers = Array.from({ length: 5 });
  return (
    <div
      className="scene inline-block"
      style={{ width: size, height: size * 1.2 }}
      role="img"
      aria-label="Splitting document into chunks"
    >
      <div className="preserve-3d relative h-full w-full">
        {layers.map((_, i) => (
          <div
            key={i}
            className="chunk-layer absolute inset-x-0 rounded-[2px] border border-edge"
            style={
              {
                "--i": layers.length - i,
                top: `${i * (100 / layers.length)}%`,
                height: `${88 / layers.length}%`,
                background:
                  i === 0
                    ? "var(--color-ink)"
                    : "color-mix(in srgb, var(--color-ink) 14%, var(--color-surface-1))",
              } as React.CSSProperties
            }
          />
        ))}
      </div>
    </div>
  );
}
