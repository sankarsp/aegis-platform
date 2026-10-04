import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";
import { copyText, Kpi, Loading, Modal, PageHead, Pill, useLoad, useToast, Bar } from "../components/ui";
import type { EvidencePack } from "../types";

function Sparkline({ values }: { values: number[] }) {
  const W = 560, H = 120, pl = 34, pr = 12, pt = 10, pb = 22, lo = 95, hi = 97.5, n = values.length;
  const X = (i: number) => pl + (i * (W - pl - pr)) / (n - 1);
  const Y = (v: number) => pt + ((hi - Math.max(lo, Math.min(hi, v))) / (hi - lo)) * (H - pt - pb);
  const d = values.map((v, i) => `${i ? "L" : "M"}${X(i).toFixed(1)} ${Y(v).toFixed(1)}`).join("");
  const last = values[n - 1];
  return (
    <svg className="spark" viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label={`Average data quality over 30 days, now ${last}%`}>
      {[95, 96, 97].map((g) => (
        <g key={g}><line x1={pl} x2={W - pr} y1={Y(g)} y2={Y(g)} /><text x={pl - 6} y={Y(g) + 3} textAnchor="end">{g}%</text></g>
      ))}
      <path className="area" d={`${d}L${X(n - 1)} ${H - pb}L${X(0)} ${H - pb}Z`} />
      <path className="ln" d={d} />
      <circle cx={X(n - 1)} cy={Y(last)} r={3.5} />
      <text x={pl} y={H - 6}>30 days ago</text>
      <text x={W - pr} y={H - 6} textAnchor="end">Today {last.toFixed(1)}%</text>
    </svg>
  );
}

export default function OverviewPage() {
  const { data, error } = useLoad(api.overview);
  const [pack, setPack] = useState<EvidencePack | null>(null);
  const toast = useToast();
  const nav = useNavigate();
  if (!data) return <Loading error={error} />;
  const k = data.kpis;
  const genPack = async () => {
    try { setPack(await api.evidencePack(data.reports[0].id)); } catch (e) { toast((e as Error).message); }
  };
  return (
    <>
      <PageHead title="Governance health" intro="Every critical data element and model traced, measured, owned, protected and attested."
        actions={<button className="btn" onClick={genPack}>Generate evidence pack</button>} />
      <div className="kpis">
        <Kpi label="Lineage coverage" value={k.lineageCoverage} unit="%" sub={`Average across ${k.cdesTotal} CDEs`} pct={k.lineageCoverage} tone={k.lineageCoverage < 95 ? "warn" : "good"} />
        <Kpi label="Data quality" value={k.dataQuality.toFixed(1)} unit="%" sub="Lowest rule result per CDE" pct={k.dataQuality} tone={k.dataQuality < 97 ? "warn" : "good"} />
        <Kpi label="CDEs with owner" value={k.cdesOwned} unit={`/${k.cdesTotal}`} sub={k.cdesOwned < k.cdesTotal ? `${k.cdesTotal - k.cdesOwned} orphaned` : "All owned"} pct={(k.cdesOwned / k.cdesTotal) * 100} tone={k.cdesOwned < k.cdesTotal ? "crit" : "good"} />
        <Kpi label="Recertification" value={k.recertDone} unit={`/${k.recertTotal}`} sub="Items attested this cycle" pct={(k.recertDone / k.recertTotal) * 100} />
        <Kpi label="Open quality issues" value={k.openIssues} sub={`${k.criticalIssues} critical`} />
        <Kpi label="AI models" value={k.models} sub={`${k.modelsWithAlerts} with open alerts`} />
      </div>
      <div className="grid g2">
        <section className="panel">
          <header><h2>Needs attention</h2><span className="muted" style={{ fontSize: 12.5 }}>{data.attention.length} items</span></header>
          <div className="list">
            {data.attention.map((a, i) => (
              <div key={i}>
                <div className={`stripe ${a.level}`}><div className="t">{a.title}</div><div className="d">{a.detail}</div></div>
                <button className="btn sm" onClick={() => nav(a.go)}>Open</button>
              </div>
            ))}
          </div>
        </section>
        <section className="panel">
          <header><h2>Average data quality, last 30 days</h2></header>
          <div className="body"><Sparkline values={data.qualityTrend} /></div>
        </section>
      </div>
      <section className="panel">
        <header><h2>Regulatory reports</h2><span className="muted" style={{ fontSize: 12.5 }}>Select a report to see its lineage</span></header>
        <div className="tbl"><table>
          <thead><tr><th>Report</th><th>Cadence</th><th>Lineage completeness</th><th>Quality gate</th></tr></thead>
          <tbody>{data.reports.map((r) => (
            <tr key={r.id} className="click" onClick={() => nav(`/lineage/${r.id}`)}>
              <td><Link to={`/lineage/${r.id}`} style={{ color: "inherit", fontWeight: 600, textDecoration: "none" }}>{r.name}</Link><div className="muted" style={{ fontSize: 12 }}>{r.regulation}</div></td>
              <td className="mono">{r.cadence}</td>
              <td style={{ minWidth: 120 }}><div className="row" style={{ gap: 8 }}><div style={{ flex: 1 }}><Bar pct={r.completeness} tone={r.completeness < 100 ? "warn" : "good"} /></div><span className="mono">{r.completeness}%</span></div></td>
              <td>{r.gate.held ? <Pill tone="crit">Held</Pill> : <Pill tone="good">Clear</Pill>}</td>
            </tr>
          ))}</tbody>
        </table></div>
      </section>
      <section className="panel">
        <header><h2>Recent activity</h2><div className="row">{data.auditChainIntact ? <Pill tone="good">Audit chain intact</Pill> : <Pill tone="crit">Audit chain broken</Pill>}<Link className="btn sm" to="/audit">Full audit log</Link></div></header>
        <div className="tbl"><table><tbody>{data.recentActivity.map((a) => (
          <tr key={a.id}><td className="mono muted" style={{ whiteSpace: "nowrap" }}>{a.ts}</td><td><b>{a.actor}</b></td><td>{a.action}</td><td className="mono">{a.object}</td></tr>
        ))}</tbody></table></div>
      </section>
      {pack && (
        <Modal title={`Evidence pack ${pack.id}`} onClose={() => setPack(null)}>
          <p className="muted" style={{ margin: 0 }}>SHA-256 {pack.sha256}</p>
          <pre>{pack.text}</pre>
          <button className="btn primary" onClick={() => copyText(pack.text, toast)}>Copy text</button>
        </Modal>
      )}
    </>
  );
}
