import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import { Bar, ClassTag, Kpi, Loading, PageHead, Pill, StatusPill, useLoad } from "../components/ui";
import type { RailSummary } from "../types";

const usd = (n: number) => new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", notation: "compact", maximumFractionDigits: 1 }).format(n);
const count = (n: number) => new Intl.NumberFormat("en-US").format(n);
const today = new Date().toISOString().slice(0, 10);
const isUpcoming = (d: string) => d >= today.slice(0, d.length);
const fmtDate = (d: string) => {
  const [y, m, day] = d.split("-").map(Number);
  const month = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][m - 1];
  return day ? `${day} ${month} ${y}` : `${month} ${y}`;
};

function health(r: RailSummary) {
  if (r.quality === "breach") return <Pill tone="crit">Breach</Pill>;
  if (r.quality === "warn" || r.rateOver) return <Pill tone="warn">Watch</Pill>;
  return <Pill tone="good">Healthy</Pill>;
}

function Detail({ id, names }: { id: string; names: Record<string, string> }) {
  const { data: r, error } = useLoad(() => api.rail(id), [id]);
  if (!r) return <Loading error={error} />;
  const rate = r.metrics.returnRate;
  return (
    <div className="grid g2">
      <section className="panel"><div className="body">
        <div className="eyebrow">{r.category} · {r.region}</div>
        <h2 style={{ fontSize: 18, margin: "4px 0 6px" }}>{r.name}</h2>
        <p style={{ margin: 0, maxWidth: "65ch" }}>{r.description}</p>
        <dl className="kv" style={{ marginTop: 14 }}>
          <dt>Operator</dt><dd>{r.operator}</dd>
          <dt>Messages</dt><dd>{r.messageStandard}</dd>
          <dt>Settlement</dt><dd>{r.settlement}</dd>
          <dt>Availability</dt><dd>{r.availability}</dd>
          <dt>Limit</dt><dd>{r.limit}</dd>
          {r.routesTo.length > 0 && <><dt>Routes to</dt><dd>{r.routesTo.map((x, i) => <span key={x}>{i > 0 && ", "}<Link to={`/payments/${x}`}>{names[x] ?? x}</Link></span>)}</dd></>}
        </dl>

        <div className="eyebrow" style={{ marginTop: 18 }}>Rules that apply</div>
        <div className="list" style={{ marginTop: 6, border: "1px solid var(--line)", borderRadius: 6 }}>
          {r.regulations.map((g) => <div key={g.name} style={{ padding: "8px 12px", display: "block" }}><div className="t">{g.name}</div><div className="d">{g.note}</div></div>)}
        </div>

        <div className="eyebrow" style={{ marginTop: 18 }}>Rule and standard changes</div>
        <div className="list" style={{ marginTop: 6, border: "1px solid var(--line)", borderRadius: 6 }}>
          {r.changes.map((c) => (
            <div key={c.date + c.text} style={{ padding: "8px 12px" }}>
              <div style={{ minWidth: 0 }}><div className="mono muted">{fmtDate(c.date)}</div><div style={{ fontSize: 13.5 }}>{c.text}</div></div>
              {isUpcoming(c.date) ? <Pill tone="warn">Upcoming</Pill> : <Pill>In effect</Pill>}
            </div>
          ))}
        </div>

        <div className="eyebrow" style={{ marginTop: 18 }}>Controls</div>
        <ul style={{ margin: "6px 0 0", paddingLeft: 18, fontSize: 13.5 }}>{r.controls.map((c) => <li key={c}>{c}</li>)}</ul>
      </div></section>

      <section className="panel"><div className="body">
        <div className="eyebrow">Last 30 days</div>
        <div className="row" style={{ gap: 24, marginTop: 6 }}>
          <div><div className="mono muted">Payments</div><b style={{ fontSize: 20 }}>{count(r.metrics.volume30d)}</b></div>
          <div><div className="mono muted">Value</div><b style={{ fontSize: 20 }}>{usd(r.metrics.value30dUsd)}</b></div>
          <div><div className="mono muted">Screened</div><b style={{ fontSize: 20 }}>{r.metrics.screeningPct}%</b></div>
          {r.metrics.travelRulePct !== null && <div><div className="mono muted">Travel Rule complete</div><b style={{ fontSize: 20 }}>{r.metrics.travelRulePct}%</b></div>}
        </div>
        <div style={{ marginTop: 14 }}>
          <div className="row" style={{ justifyContent: "space-between", fontSize: 13 }}><span>{rate.label}</span><span className="mono">{rate.value}{rate.unit} <span className="muted">limit {rate.threshold}{rate.unit}</span></span></div>
          <div className="bar" style={{ position: "relative", overflow: "visible", marginTop: 4 }}>
            <i className={r.rateOver ? "crit" : "good"} style={{ width: `${Math.min(100, (rate.value / (rate.threshold * 2)) * 100)}%` }} />
            <span aria-hidden="true" style={{ position: "absolute", left: "50%", top: -3, height: 12, borderLeft: "2px solid var(--fg)" }} />
          </div>
        </div>
        {r.alerts.length > 0 && <div style={{ marginTop: 14, display: "grid", gap: 8 }}>{r.alerts.map((a) => <div key={a.text} className={`stripe ${a.level}`} style={{ fontSize: 13 }}>{a.text}</div>)}</div>}

        <div className="eyebrow" style={{ marginTop: 18 }}>Data quality rules</div>
        <div className="tbl" style={{ marginTop: 6 }}><table>
          <thead><tr><th>Rule</th><th style={{ textAlign: "right" }}>Result</th><th>Status</th></tr></thead>
          <tbody>{r.rules.map((x) => (
            <tr key={x.id}><td><span className="mono muted">{x.id}</span> {x.name}<div className="mono muted">{x.cdeId}</div></td>
              <td className="num">{x.lastValue.toFixed(2)}% <span className="muted">/ {x.threshold}%</span></td><td><StatusPill status={x.status} /></td></tr>
          ))}</tbody>
        </table></div>

        {r.issues.length > 0 && (<>
          <div className="eyebrow" style={{ marginTop: 18 }}>Open issues</div>
          <div className="list" style={{ marginTop: 6 }}>{r.issues.map((i) => (
            <div key={i.id} style={{ padding: "8px 0" }}><div style={{ minWidth: 0 }}><div className="t">{i.id} · {i.ruleId}</div><div className="d">{i.note}</div></div><Link className="btn sm" to="/quality">Open</Link></div>
          ))}</div>
        </>)}

        <div className="eyebrow" style={{ marginTop: 18 }}>Critical data elements</div>
        <div className="tbl" style={{ marginTop: 6 }}><table><tbody>{r.cdes.map((c) => (
          <tr key={c.id}><td><Link className="mono" to={`/catalog?q=${encodeURIComponent(c.id)}`}>{c.id}</Link><div className="muted" style={{ fontSize: 12.5 }}>{c.name} · owner {c.owner ?? "none"}</div></td>
            <td><ClassTag cls={c.classification} /></td><td><StatusPill status={c.status} /></td></tr>
        ))}</tbody></table></div>

        <div className="eyebrow" style={{ marginTop: 18 }}>Models and reports</div>
        <div className="list" style={{ marginTop: 6 }}>
          {r.models.map((m) => (
            <div key={m.id} style={{ padding: "8px 0" }}>
              <div><Link className="t" to={`/ai/${m.id}`}>{m.name} {m.version}</Link><div className="d">AI model · {m.tier} risk · {m.stage}</div></div>
              {m.alerts.length ? <Pill tone="warn">{m.alerts.length} alert{m.alerts.length > 1 ? "s" : ""}</Pill> : <Pill tone="good">Healthy</Pill>}
            </div>
          ))}
          {r.report && (
            <div style={{ padding: "8px 0" }}>
              <div><Link className="t" to={`/lineage/${r.report.id}`}>{r.report.name}</Link><div className="d">Report · lineage {r.report.completeness}% verified</div></div>
              {r.report.gate.held ? <Pill tone="crit">Held</Pill> : <Pill tone="good">Clear</Pill>}
            </div>
          )}
        </div>
      </div></section>
    </div>
  );
}

export default function Payments() {
  const { railId } = useParams();
  const nav = useNavigate();
  const { data, error } = useLoad(api.rails);
  if (!data) return <Loading error={error} />;
  const sel = railId ?? data[0]?.id;
  const names = Object.fromEntries(data.map((r) => [r.id, r.name]));
  const vol = data.filter((r) => r.category !== "Product").reduce((a, r) => a + r.metrics.volume30d, 0);
  const val = data.filter((r) => r.category !== "Product").reduce((a, r) => a + r.metrics.value30dUsd, 0);
  const tr = data.map((r) => r.metrics.travelRulePct).filter((x): x is number => x !== null);
  const watching = data.filter((r) => r.quality !== "pass" || r.rateOver).length;
  return (
    <>
      <PageHead title="Payment rails"
        intro="Every payment type the business offers, with the data each one carries, the rules that apply, the quality checks on that data and the models that score it." />
      <div className="kpis">
        <Kpi label="Rails" value={data.length} sub="ACH, wires, real-time and cross-border" />
        <Kpi label="Payments, 30 days" value={count(vol)} sub={`${usd(val)} sent; wires counted once`} />
        <Kpi label="Sanctions screening" value={Math.min(...data.map((r) => r.metrics.screeningPct))} unit="%" sub="Lowest across rails" />
        <Kpi label="Travel Rule data" value={Math.min(...tr)} unit="%" sub="Lowest completeness, transfers of $3,000+" pct={Math.min(...tr)} tone={Math.min(...tr) < 100 ? "warn" : "good"} />
        <Kpi label="Rails to watch" value={watching} sub="Quality breach or rate over limit" />
      </div>
      <section className="panel">
        <header><h2>All rails</h2><span className="muted" style={{ fontSize: 12.5 }}>Select a rail to see its rules, data and models</span></header>
        <div className="tbl"><table>
          <thead><tr><th>Rail</th><th>Type</th><th>Messages</th><th>Limit</th><th style={{ textAlign: "right" }}>Payments, 30 days</th><th>Key rate</th><th>Health</th></tr></thead>
          <tbody>{data.map((r) => (
            <tr key={r.id} className={`click ${r.id === sel ? "sel" : ""}`} onClick={() => nav(`/payments/${r.id}`)}>
              <td><b>{r.name}</b><div className="muted" style={{ fontSize: 12 }}>{r.region}</div></td>
              <td>{r.category}</td>
              <td style={{ maxWidth: 240 }}>{r.messageStandard}</td>
              <td style={{ maxWidth: 220 }}>{r.limit}</td>
              <td className="num">{count(r.metrics.volume30d)}</td>
              <td style={{ minWidth: 150 }}><div style={{ fontSize: 12.5 }}>{r.metrics.returnRate.label}</div>
                <div className="row" style={{ gap: 6 }}><div style={{ flex: 1 }}><Bar pct={(r.metrics.returnRate.value / (r.metrics.returnRate.threshold * 2)) * 100} tone={r.rateOver ? "crit" : "good"} /></div>
                  <span className="mono">{r.metrics.returnRate.value}{r.metrics.returnRate.unit}</span></div></td>
              <td>{health(r)}{r.upcomingChanges > 0 && <div style={{ marginTop: 4 }}><Pill tone="info">{r.upcomingChanges} upcoming change{r.upcomingChanges > 1 ? "s" : ""}</Pill></div>}</td>
            </tr>
          ))}</tbody>
        </table></div>
      </section>
      {sel && <Detail id={sel} names={names} />}
    </>
  );
}
