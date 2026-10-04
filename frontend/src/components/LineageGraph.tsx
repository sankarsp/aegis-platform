import type { LineageEdge, LineageNode } from "../types";

const CW = 176, NW = 150, NH = 46, RH = 66, TOP = 40;
const HEADS = ["Source", "Ingestion", "Staging", "Integration", "Mart", "Report"];
const DOT: Record<string, string> = { pass: "dot-good", warn: "dot-warn", breach: "dot-crit", none: "dot-none" };

export function LineageGraph({ nodes, edges, selected, onSelect }: {
  nodes: LineageNode[]; edges: LineageEdge[]; selected: string | null; onSelect: (id: string | null) => void;
}) {
  const maxRow = Math.max(0, ...nodes.map((n) => n.row));
  const W = 16 + 5 * CW + NW + 16, H = TOP + (maxRow + 1) * RH + 10;
  const pos = Object.fromEntries(nodes.map((n) => [n.id, { x: 16 + n.col * CW, y: TOP + n.row * RH }]));
  return (
    <div className="lineage">
      <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Lineage graph">
        <defs>
          <marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M0 0L10 5L0 10z" fill="var(--muted)" />
          </marker>
        </defs>
        {HEADS.map((h, i) => <text key={h} className="colh" x={16 + i * CW} y={22}>{h}</text>)}
        {edges.map((e) => {
          const a = pos[e.source], b = pos[e.target];
          if (!a || !b) return null;
          const x1 = a.x + NW, y1 = a.y + NH / 2, x2 = b.x - 4, y2 = b.y + NH / 2, mx = (x1 + x2) / 2;
          const hot = selected && (e.source === selected || e.target === selected);
          const cls = ["e", e.kind !== "auto" ? e.kind : "", hot ? "hot" : ""].join(" ");
          return <path key={e.id} className={cls} d={`M${x1} ${y1}C${mx} ${y1} ${mx} ${y2} ${x2} ${y2}`} markerEnd="url(#arr)" />;
        })}
        {nodes.map((n) => {
          const p = pos[n.id];
          const cls = ["node", n.isReport ? "report" : "", n.isEuc ? "euc" : "", selected === n.id ? "sel" : ""].join(" ");
          return (
            <g key={n.id} className={cls} tabIndex={0} role="button" aria-label={`${n.label}, ${n.sub}`}
              onClick={() => onSelect(n.id)} onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onSelect(n.id); } }}>
              <rect x={p.x} y={p.y} width={NW} height={NH} rx={7} />
              <circle className={DOT[n.status]} cx={p.x + NW - 12} cy={p.y + 12} r={4} />
              <text className="lbl" x={p.x + 10} y={p.y + 20}>{n.label}</text>
              <text className="sub" x={p.x + 10} y={p.y + 36}>{n.sub}</text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
