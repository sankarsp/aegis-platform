import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import { Bar, Kpi, Loading, PageHead, Pill, StatusPill, useAction, useLoad } from "../components/ui";
import type { AiModel } from "../types";

const airTone = (v: number) => (v < 0.8 ? "crit" : v < 0.85 ? "warn" : "good");
const psiTone = (p: number) => (p >= 0.25 ? "crit" : p >= 0.1 ? "warn" : "good");
const health = (m: AiModel) => {
  const real = m.alerts.filter((a) => a.level !== "info");
  return real.some((a) => a.level === "crit") ? "crit" : real.length ? "warn" : "good";
};

export default function AiGovernance() {
  const { modelId = "M1" } = useParams();
  const nav = useNavigate();
  const { data, error, setData } = useLoad(api.models);
  const { run, busy } = useAction();
  if (!data) return <Loading error={error} />;
  const m = data.find((x) => x.id === modelId) ?? data[0];
  const act = (action: Parameters<typeof api.modelAction>[1], msg: (r: AiModel) => string) =>
    run(() => api.modelAction(m.id, action), (r) => { setData(data.map((x) => (x.id === r.id ? r : x))); return msg(r); });
  const paused = m.stage.startsWith("Paused");
  const pending = m.approvals.find((a) => !a.approved);

  return (
    <>
      <PageHead title="AI governance" intro="One inventory for every model and AI system, tiered by risk, tied to the data it uses, and monitored for drift, fairness and generative AI safety." />
      <div className="kpis">
        <Kpi label="Models in inventory" value={data.length} sub={`${data.filter((x) => x.llmEvals).length} generative AI systems`} />
        <Kpi label="High-risk models" value={data.filter((x) => x.tier === "High").length} sub="Credit decisions and AML" />
        <Kpi label="Models with alerts" value={data.filter((x) => health(x) !== "good").length} sub="Fairness, drift, validation or data" />
        <Kpi label="Awaiting approval" value={data.filter((x) => x.approvals.some((a) => !a.approved)).length} sub="Approval chain not complete" />
      </div>
      <section className="panel">
        <header><h2>Model inventory</h2><span className="muted" style={{ fontSize: 12.5 }}>Select a model to see its card and monitoring</span></header>
        <div className="tbl"><table>
          <thead><tr><th>Model</th><th>Type</th><th>Risk tier</th><th>Stage</th><th>Owner</th><th>Health</th></tr></thead>
          <tbody>{data.map((x) => {
            const h = health(x), n = x.alerts.filter((a) => a.level !== "info").length;
            return (
              <tr key={x.id} className={`click ${x.id === m.id ? "sel" : ""}`} onClick={() => nav(`/ai/${x.id}`)}>
                <td><b>{x.name}</b> <span className="mono muted">{x.version}</span><div className="muted" style={{ fontSize: 12 }}>{x.use}</div></td>
                <td>{x.type}<div className="muted" style={{ fontSize: 12 }}>{x.source}</div></td>
                <td><Pill tone={x.tier === "High" ? "crit" : "warn"}>{x.tier}</Pill></td>
                <td>{x.stage.startsWith("Paused") ? <Pill tone="crit">{x.stage}</Pill> : x.stage}</td>
                <td>{x.owner}</td>
                <td>{h === "good" ? <Pill tone="good">Healthy</Pill> : <Pill tone={h}>{n} alert{n > 1 ? "s" : ""}</Pill>}</td>
              </tr>
            );
          })}</tbody>
        </table></div>
      </section>
      <div className="grid g2">
        <section className="panel"><div className="body">
          <div className="eyebrow">Model card</div>
          <h2 style={{ fontSize: 17, margin: "4px 0 2px" }}>{m.name} <span className="mono muted" style={{ fontSize: 13 }}>{m.version}</span></h2>
          <div className="muted" style={{ fontSize: 12.5 }}>{m.use}</div>
          <p className="muted" style={{ fontSize: 12, margin: "8px 0 0" }}>Each approval step must be signed by a different person.</p>
          <dl className="kv" style={{ marginTop: 14 }}>
            <dt>Risk tier</dt><dd><Pill tone={m.tier === "High" ? "crit" : "warn"}>{m.tier}</Pill></dd>
            <dt>Stage</dt><dd>{m.stage}</dd>
            <dt>Owner</dt><dd>{m.owner}</dd>
            <dt>Validation</dt><dd>{m.validator} · last {m.validated}<br /><span className="muted">next due {m.nextValidation}</span></dd>
            <dt>Explainability</dt><dd>{m.explainability}</dd>
            <dt>Input data</dt><dd>{m.dataCdes.map((c) => (
              <div key={c.id} className="row" style={{ gap: 6 }}><a className="mono" href={`/catalog?q=${encodeURIComponent(c.id)}`}>{c.id}</a>{c.status !== "pass" && <StatusPill status={c.status} />}</div>
            ))}<div className="muted" style={{ fontSize: 12, marginTop: 4 }}>Linked to the catalog; a quality breach on these CDEs raises a model alert.</div></dd>
            <dt>Obligations</dt><dd>{m.regulations.map((r) => <div key={r}>{r}</div>)}</dd>
            <dt>Controls</dt><dd>{m.controls.map((c) => <div key={c}>{c}</div>)}</dd>
          </dl>
          <div className="eyebrow" style={{ marginTop: 16 }}>Approval chain</div>
          <div className="list" style={{ marginTop: 6, border: "1px solid var(--line)", borderRadius: 6 }}>
            {m.approvals.map((a) => (
              <div key={a.step} style={{ padding: "8px 12px" }}>
                <span>{a.step}{a.by && <span className="muted" style={{ fontSize: 12 }}> · {a.by}</span>}</span>
                {a.approved ? <Pill tone="good">Approved</Pill> : <Pill tone="warn">Pending</Pill>}
              </div>
            ))}
          </div>
          {pending && <button className="btn primary sm" style={{ marginTop: 10 }} disabled={busy} onClick={() => act("approve", () => `${pending.step} approval recorded.`)}>Record approval: {pending.step}</button>}
        </div></section>

        <section className="panel"><div className="body">
          <div className="eyebrow">Monitoring</div>
          {m.performance && (() => {
            const drop = ((m.performance.baseline - m.performance.value) / m.performance.baseline) * 100;
            return (
              <div style={{ marginTop: 10 }}>
                <div className="row" style={{ justifyContent: "space-between" }}><b>{m.performance.metric}</b><span className="mono">{m.performance.value} <span className="muted">vs {m.performance.baseline} at validation</span></span></div>
                <div className="muted" style={{ fontSize: 12.5 }}>{drop > 5 ? <span style={{ color: "var(--crit)", fontWeight: 600 }}>Down {drop.toFixed(0)}% since validation</span> : "Within 5% of validated performance"}</div>
              </div>
            );
          })()}
          {m.psi !== null && (
            <div style={{ marginTop: 12 }}>
              <div className="row" style={{ justifyContent: "space-between" }}><b>Input drift (PSI)</b><Pill tone={psiTone(m.psi)}>{m.psi.toFixed(2)}</Pill></div>
              <div style={{ marginTop: 6 }}><Bar pct={(m.psi / 0.4) * 100} tone={psiTone(m.psi)} /></div>
              <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>Below 0.10 stable · 0.10 to 0.25 watch · above 0.25 retrain or review</div>
            </div>
          )}
          {m.fairness && (
            <div style={{ marginTop: 16 }}>
              <b>Fair lending: adverse impact ratio</b>
              <div className="muted" style={{ fontSize: 12 }}>Approval rate of each group divided by the reference group. Below 0.80 fails the four-fifths rule.</div>
              {m.fairness.map((f) => (
                <div key={f.group} style={{ marginTop: 8 }}>
                  <div className="row" style={{ justifyContent: "space-between", fontSize: 12.5 }}><span>{f.group}</span><span className="mono" style={f.value < 0.8 ? { color: "var(--crit)", fontWeight: 600 } : undefined}>{f.value.toFixed(2)}</span></div>
                  <div className="bar" style={{ position: "relative", overflow: "visible" }}>
                    <i className={airTone(f.value)} style={{ width: `${(f.value / 1.2) * 100}%` }} />
                    <span aria-hidden="true" style={{ position: "absolute", left: `${(0.8 / 1.2) * 100}%`, top: -3, height: 12, borderLeft: "2px solid var(--fg)" }} />
                  </div>
                </div>
              ))}
              <div className="row" style={{ marginTop: 10 }}>
                <button className="btn sm" disabled={busy} onClick={() => act("fairness-test", () => "Fairness test complete.")}>Run fairness test</button>
                {m.fairness.some((f) => f.value < 0.8) && (
                  <button className="btn sm primary" disabled={busy} onClick={() => act("mitigate", (r) => `${r.version} meets the four-fifths rule and now needs approval.`)}>Apply mitigation and retest</button>
                )}
              </div>
            </div>
          )}
          {m.llmEvals && (
            <div style={{ marginTop: 12 }}>
              <b>Generative AI evaluation suite</b>
              <div className="tbl" style={{ marginTop: 6 }}><table><tbody>{m.llmEvals.map((e) => (
                <tr key={e.name}><td>{e.name}</td><td className="num">{e.value.toFixed(1)}%</td><td className="num muted">≥ {e.target}%</td>
                  <td><StatusPill status={e.value >= e.target ? "pass" : e.target - e.value <= 1.5 ? "warn" : "breach"} /></td></tr>
              ))}</tbody></table></div>
              <button className="btn sm" style={{ marginTop: 10 }} disabled={busy} onClick={() => act("evaluate", () => "Evaluation suite complete.")}>Run evaluation suite</button>
            </div>
          )}
          {m.alerts.length > 0 && <div style={{ marginTop: 16, display: "grid", gap: 8 }}>{m.alerts.map((a) => <div key={a.text} className={`stripe ${a.level}`} style={{ fontSize: 13 }}>{a.text}</div>)}</div>}
          <div className="row" style={{ marginTop: 16, borderTop: "1px solid var(--line)", paddingTop: 14 }}>
            {m.stage !== "Awaiting approval" && (
              <button className={`btn sm ${paused ? "primary" : "danger"}`} disabled={busy}
                onClick={() => act("pause", (r) => (r.stage.startsWith("Paused") ? "Model paused. Decisions use the rules-based fallback." : "Model resumed."))}>
                {paused ? "Resume model" : "Pause model, use fallback"}
              </button>
            )}
            <button className="btn sm" disabled={busy} onClick={() => act("revalidate", (r) => `Revalidation requested from ${r.validator}.`)}>Request revalidation</button>
          </div>
        </div></section>
      </div>
    </>
  );
}
