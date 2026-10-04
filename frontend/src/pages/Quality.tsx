import { api } from "../api";
import { Bar, Loading, PageHead, Pill, StatusPill, useAction, useLoad } from "../components/ui";

const sevTone = (s: string) => (s === "Critical" ? "crit" : s === "High" ? "warn" : "info");

export default function Quality() {
  const rules = useLoad(api.rules);
  const issues = useLoad(api.issues);
  const gates = useLoad(api.gates);
  const { run, busy } = useAction();
  const refresh = () => { rules.reload(); issues.reload(); gates.reload(); };
  if (!rules.data || !issues.data || !gates.data) return <Loading error={rules.error || issues.error || gates.error} />;

  const dims: Record<string, number[]> = {};
  rules.data.forEach((r) => (dims[r.dimension] ??= []).push(r.lastValue));
  const open = issues.data.filter((i) => i.status !== "Closed").length;
  const today = new Date().toISOString().slice(0, 10);

  return (
    <>
      <PageHead title="Data quality"
        intro="Rules run inside the warehouse; only results come back. A breach on any upstream CDE holds the regulatory report until it is resolved."
        actions={<button className="btn primary" disabled={busy}
          onClick={() => run(api.runRules, (r) => (r.opened.length ? `${r.opened.length} new issue(s) opened` : "Checks complete. No new breaches."), refresh)}>Run all checks</button>} />
      <div className="grid g-side">
        <section className="panel">
          <header><h2>Rules</h2><span className="muted" style={{ fontSize: 12.5 }}>{rules.data.length} active · thresholds set by data owners</span></header>
          <div className="tbl"><table>
            <thead><tr><th>ID</th><th>Rule</th><th>Dimension</th><th style={{ textAlign: "right" }}>Threshold</th><th style={{ textAlign: "right" }}>Last result</th><th>Status</th></tr></thead>
            <tbody>{rules.data.map((r) => (
              <tr key={r.id}>
                <td className="mono">{r.id}</td>
                <td><b>{r.name}</b><div className="mono muted">{r.cdeId}</div></td>
                <td>{r.dimension}</td>
                <td className="num">≥ {r.threshold}%</td>
                <td className="num">{r.lastValue.toFixed(2)}%</td>
                <td><StatusPill status={r.status} /></td>
              </tr>
            ))}</tbody>
          </table></div>
        </section>
        <div className="grid" style={{ alignContent: "start" }}>
          <section className="panel">
            <header><h2>Pre-submission gates</h2></header>
            <div className="list">{gates.data.map((g) => (
              <div key={g.reportId}>
                <div><div className="t">{g.name}</div><div className="d">{g.held ? `Held: breach on ${g.breached_cdes.join(", ")}` : "All upstream CDEs within threshold"}</div></div>
                {g.held ? <Pill tone="crit">Held</Pill> : <Pill tone="good">Clear</Pill>}
              </div>
            ))}</div>
          </section>
          <section className="panel">
            <header><h2>By dimension</h2></header>
            <div className="body grid" style={{ gap: 10 }}>{Object.entries(dims).map(([k, vs]) => {
              const v = vs.reduce((a, b) => a + b, 0) / vs.length;
              return <div key={k}><div className="row" style={{ justifyContent: "space-between", fontSize: 12.5 }}><span>{k}</span><span className="mono">{v.toFixed(1)}%</span></div><Bar pct={v} tone={v < 97 ? "warn" : "good"} /></div>;
            })}</div>
          </section>
        </div>
      </div>
      <section className="panel">
        <header><h2>Issues</h2><span className="muted" style={{ fontSize: 12.5 }}>{open} open</span></header>
        <div className="list">{issues.data.map((i) => (
          <div key={i.id}>
            <div className={`stripe ${i.status === "Closed" ? "" : sevTone(i.severity)}`} style={{ minWidth: 0 }}>
              <div className="row" style={{ gap: 8 }}>
                <span className="t">{i.id}</span>
                <Pill tone={i.status === "Closed" ? "good" : sevTone(i.severity)}>{i.status === "Closed" ? "Closed" : i.severity}</Pill>
                {i.status !== "Closed" && i.due <= today && <Pill tone="crit">SLA due</Pill>}
              </div>
              <div className="d"><span className="mono">{i.cdeId}</span> · {i.ruleId} · {i.owner} · due {i.due}</div>
              <div style={{ fontSize: 13, marginTop: 4 }}>{i.note}</div>
            </div>
            {i.status !== "Closed" && (
              <div className="row" style={{ flex: "none" }}>
                <span className="muted" style={{ fontSize: 12 }}>{i.status}</span>
                <button className="btn sm" disabled={busy} onClick={() => run(() => api.resolveIssue(i.id), () => `${i.id} resolved. Downstream gates re-evaluated.`, refresh)}>Mark resolved</button>
              </div>
            )}
          </div>
        ))}</div>
      </section>
    </>
  );
}
