import { useState } from "react";
import { api } from "../api";
import { Kpi, Loading, PageHead, Pill, useAction, useLoad } from "../components/ui";
import type { Suggestion } from "../types";

export default function Access() {
  const scans = useLoad(api.scans);
  const policies = useLoad(api.policies);
  const { run, busy } = useAction();
  const [col, setCol] = useState("customer_email_address");
  const [sugg, setSugg] = useState<Suggestion | null>(null);
  if (!scans.data || !policies.data) return <Loading error={scans.error || policies.error} />;
  const proposed = scans.data.filter((s) => s.status === "Proposed").length;
  const enforced = policies.data.filter((p) => p.mode === "Enforced").length;
  return (
    <>
      <PageHead title="Access and privacy" intro="Scanners classify sensitive columns; confirmed labels flow down lineage, and policies compile to native masking and grants in each platform." />
      <div className="kpis">
        <Kpi label="Proposed labels" value={proposed} sub="Waiting for steward review" />
        <Kpi label="Confirmed labels" value={scans.data.filter((s) => s.status === "Confirmed").length} sub="Used to train label suggestions" />
        <Kpi label="Policies enforced" value={enforced} unit={`/${policies.data.length}`} sub="Others in monitor mode" />
      </div>
      <section className="panel">
        <header><h2>Sensitive data discovery</h2></header>
        <div className="tbl"><table>
          <thead><tr><th>Column</th><th>Detected</th><th style={{ textAlign: "right" }}>Confidence</th><th>Label</th><th /></tr></thead>
          <tbody>{scans.data.map((s) => (
            <tr key={s.id}>
              <td className="mono">{s.column}</td><td>{s.label}</td><td className="num">{s.confidence}%</td>
              <td>{s.status === "Confirmed" ? <Pill tone="good">Confirmed</Pill> : s.status === "Rejected" ? <Pill>Rejected</Pill> : <Pill tone="warn">Proposed</Pill>}</td>
              <td>{s.status === "Proposed" && (
                <div className="row" style={{ flexWrap: "nowrap" }}>
                  <button className="btn sm primary" disabled={busy} onClick={() => run(() => api.decideScan(s.id, "Confirmed"), () => "Label confirmed and propagated downstream.", scans.reload)}>Confirm</button>
                  <button className="btn sm" disabled={busy} onClick={() => run(() => api.decideScan(s.id, "Rejected"), () => "Label rejected.", scans.reload)}>Reject</button>
                </div>
              )}</td>
            </tr>
          ))}</tbody>
        </table></div>
      </section>
      <section className="panel">
        <header><h2>Suggest a label for a new column</h2><span className="muted" style={{ fontSize: 12.5 }}>Nearest steward-confirmed columns in the vector index</span></header>
        <div className="body grid" style={{ gap: 10 }}>
          <div className="searchbar">
            <input type="search" id="new-column" value={col} onChange={(e) => setCol(e.target.value)} aria-label="Column name" />
            <button className="btn primary" disabled={busy || col.trim().length < 2} onClick={() => run(() => api.suggestLabel(col), setSugg)}>Suggest label</button>
          </div>
          {sugg && (sugg.suggestion
            ? <div className="stripe info"><b>{sugg.suggestion}</b> <span className="mono muted">similarity {sugg.confidence?.toFixed(2)}</span>
                <div className="muted" style={{ fontSize: 12.5 }}>Closest: {sugg.neighbours.map((n) => `${n.column} (${n.label})`).join("; ")}. {sugg.note}</div></div>
            : <span className="muted">No confirmed labels to compare with yet.</span>)}
        </div>
      </section>
      <section className="panel">
        <header><h2>Access policies</h2><span className="muted" style={{ fontSize: 12.5 }}>Attribute-based · enforced natively</span></header>
        <div className="list">{policies.data.map((p) => (
          <div key={p.id}>
            <div style={{ minWidth: 0 }}><div className="t">{p.name}</div><div className="mono" style={{ marginTop: 2, overflowWrap: "anywhere" }}>{p.rule}</div><div className="d">{p.scope}</div></div>
            <div className="row" style={{ flex: "none" }}>
              <Pill tone={p.mode === "Enforced" ? "good" : "warn"}>{p.mode}</Pill>
              <button className="btn sm" disabled={busy} onClick={() => run(() => api.togglePolicy(p.id), (r) => `${r.name}: ${r.mode}`, policies.reload)}>{p.mode === "Enforced" ? "Switch to monitor" : "Enforce"}</button>
            </div>
          </div>
        ))}</div>
      </section>
    </>
  );
}
