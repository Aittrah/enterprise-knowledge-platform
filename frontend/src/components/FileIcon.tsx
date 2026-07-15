/** Document-type icons, Google Drive style: one glyph, one color per
 * format. Deliberately no blue anywhere in the set. */

const TYPE_STYLES: Record<string, { color: string; label: string }> = {
  pdf: { color: "#c5221f", label: "PDF" },
  docx: { color: "#0e7a63", label: "DOC" },
  doc: { color: "#0e7a63", label: "DOC" },
  pptx: { color: "#e37400", label: "PPT" },
  ppt: { color: "#e37400", label: "PPT" },
  csv: { color: "#1e8e3e", label: "CSV" },
  tsv: { color: "#1e8e3e", label: "CSV" },
  xlsx: { color: "#1e8e3e", label: "XLS" },
  txt: { color: "#6b6862", label: "TXT" },
  md: { color: "#6b6862", label: "MD" },
  html: { color: "#b3540e", label: "HTM" },
  image: { color: "#8430ce", label: "IMG" },
  png: { color: "#8430ce", label: "IMG" },
  jpg: { color: "#8430ce", label: "IMG" },
};

export function fileStyle(typeOrName: string) {
  const key = typeOrName.toLowerCase().split(".").pop() ?? "";
  return TYPE_STYLES[key] ?? { color: "#6b6862", label: key.slice(0, 3).toUpperCase() || "FILE" };
}

export function FileIcon({
  type,
  size = 28,
  className = "",
}: {
  type: string;
  size?: number;
  className?: string;
}) {
  const { color, label } = fileStyle(type);
  return (
    <svg
      width={size}
      height={size * 1.25}
      viewBox="0 0 32 40"
      className={className}
      aria-hidden
    >
      {/* page with folded corner */}
      <path
        d="M4 3a3 3 0 0 1 3-3h14l7 7v30a3 3 0 0 1-3 3H7a3 3 0 0 1-3-3V3z"
        fill={color}
        opacity="0.14"
      />
      <path
        d="M4 3a3 3 0 0 1 3-3h14l7 7v30a3 3 0 0 1-3 3H7a3 3 0 0 1-3-3V3z"
        fill="none"
        stroke={color}
        strokeWidth="1.6"
      />
      <path d="M21 0v7h7" fill="none" stroke={color} strokeWidth="1.6" />
      <rect x="4" y="22" width="24" height="11" rx="2" fill={color} />
      <text
        x="16"
        y="30.5"
        textAnchor="middle"
        fontSize="8"
        fontWeight="700"
        fill="#ffffff"
        style={{ fontFamily: "var(--font-mono)", letterSpacing: "0.5px" }}
      >
        {label}
      </text>
    </svg>
  );
}

/** Large outline document used in the upload zone. */
export function UploadDocGlyph({ active }: { active: boolean }) {
  const stroke = active ? "var(--color-ink)" : "var(--color-ink-muted)";
  return (
    <svg
      width="64"
      height="80"
      viewBox="0 0 64 80"
      aria-hidden
      className={active ? "anim-pop" : "anim-float"}
    >
      <path
        d="M8 6a5 5 0 0 1 5-5h28l15 15v58a5 5 0 0 1-5 5H13a5 5 0 0 1-5-5V6z"
        fill="var(--color-surface-1)"
        stroke={stroke}
        strokeWidth="2"
        strokeDasharray={active ? "none" : "6 4"}
      />
      <path d="M41 1v15h15" fill="none" stroke={stroke} strokeWidth="2" />
      <line x1="18" y1="34" x2="46" y2="34" stroke={stroke} strokeWidth="2" strokeLinecap="round" />
      <line x1="18" y1="44" x2="46" y2="44" stroke={stroke} strokeWidth="2" strokeLinecap="round" />
      <line x1="18" y1="54" x2="36" y2="54" stroke={stroke} strokeWidth="2" strokeLinecap="round" />
      {/* upward arrow */}
      <g transform="translate(32, 66)">
        <circle r="9" fill={active ? "var(--color-ink)" : "var(--color-surface-2)"} />
        <path
          d="M0 4 V-4 M-3.5 -0.5 L0 -4 L3.5 -0.5"
          stroke={active ? "var(--color-surface-0)" : stroke}
          strokeWidth="2"
          strokeLinecap="round"
          fill="none"
        />
      </g>
    </svg>
  );
}
