import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import { LineageGraph } from "../components/LineageGraph";
import { Bar, copyText, Loading, Modal, PageHead, Pill, StatusPill, useAction, useLoad, useToast } from "../components/ui";
import type { EvidencePack, Impact } from "../types";

export default function Lineage() {
  const { reportId = "recon" } = useParams();
  const nav = useNavigate();
  const toast = useToast();
  const { data: reports } = useLoad(api.reports);
  const { data: rp, error, reload } = useLoad(() => api.report(reportId), [reportId]);
  const [sel, setSel] = useState<string | null>(null);
  const [impact, setImpact] = useState<Impact | null>(null);
  const [pack, setPack] = useState<EvidencePack | null>(null);
  const { run, busy } = useAction();
  if (!rp) return <Loading error={error} />;

  const node = rp.nodes.find((n) => n.id === sel) ?? null;
  const manualOut = node ? rp.edges.filter((e) => e.source === node.id && e.kind === "manual") : [];
  const inbound = node ? rp.edges.filter((e) => e.target === node.id).length : 0;

  return (
    <>
      <PageHead title="Lineage and BCBS 239"
        intro="Column-level lineage from source system to regulatory report, harvested from dbt, Kafka and warehouse logs. Dashed hops are manual."
        actions={<>
          <select aria-label="Report" value={reportId} onChange={(e) => { setSel(null); nav(`/lineage/${e.target.value}`); }}>
            {reports?.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
          </select>
          <button className="btn" onClick={() => run(() => api.evidencePack(rp.id), (p) => { setPack(p); })}>Evidence pack</button>
        </>} />
      <div className="grid g-side">
        <section className="panel">
          <header><div className="legend"><span><i />Automated</span><span><i className="m" />Manual, unverified</span><span><i className="s" />Manual, signed off</span></div></header>
          <div className="body"><LineageGraph nodes={rp.nodes} edges={rp.edges} selected={sel} onSelect={setSel} /></div>
        </section>
        <section className="panel"><div className="body">
          {node ? (
            <>
              <div className="eyebrow">Selected node</div>
              <h2 style={{ fontSize: 17, margin: "4px 0 2px" }}>{node.label}</h2>
              <div className="mono muted">{node.sub}</div>
              <dl className="kv" style={{ marginTop: 14 }}>
                <dt>Owner</dt><dd>{node.owner}</dd>
                <dt>CDEs</dt><dd>{node.cdeIds.length ? node.cdeIds.map((c) => {
                  const cde = rp.cdes.find((x) => x.id === c);
                  return <div key={c} className="row" style={{ gap: 6 }}><span className="mono">{c}</span>{cde && <StatusPill status={cde.status} />}</div>;
                }) : <span className="muted">None tagged</span>}</dd>
                <dt>Controls</dt><dd>{node.controls.join(", ")}</dd>
                <dt>Upstream</dt><dd>{inbound || <span className="muted">Origin system</span>}</dd>
              </dl>
              {manualOut.map((e) => (
                <div key={e.id} className="stripe warn" style={{ marginTop: 14 }}>
                  <b>Manual hop, unverified</b>
                  <div className="muted" style={{ fontSize: 12.5 }}>This source feeds the report without automated lineage. A steward must sign it off before it counts toward BCBS 239 completeness.</div>
                  <button className="btn primary sm" style={{ marginTop: 8 }} disabled={busy}
                    onClick={() => run(() => api.signOff(rp.id, e.id), (r) => `Signed off. Lineage completeness now ${r.completeness}%.`, reload)}>Sign off as steward</button>
                </div>
              ))}
              <div className="row" style={{ marginTop: 14 }}>
                <button className="btn sm" onClick={() => run(() => api.impact(rp.id, node.id), setImpact)}>Impact analysis</button>
                <button className="btn sm" onClick={() => setSel(null)}>Clear selection</button>
              </div>
            </>
          ) : (
            <>
              <div className="eyebrow">Report</div>
              <h2 style={{ fontSize: 17, margin: "4px 0 2px" }}>{rp.name}</h2>
              <div className="muted" style={{ fontSize: 12.5 }}>{rp.regulation}</div>
              <dl className="kv" style={{ marginTop: 14 }}>
                <dt>Owner</dt><dd>{rp.owner}</dd>
                <dt>Cadence</dt><dd>{rp.cadence}</dd>
                <dt>Completeness</dt><dd className="mono">{rp.completeness}% of hops verified</dd>
                <dt>Quality gate</dt><dd>{rp.gate.held
                  ? <><Pill tone="crit">Held</Pill><div className="muted" style={{ fontSize: 12, marginTop: 4 }}>Breach upstream: {rp.gate.breached_cdes.join(", ")}</div></>
                  : <Pill tone="good">Clear to file</Pill>}</dd>
              </dl>
              <div className="eyebrow" style={{ marginTop: 16 }}>BCBS 239 principle coverage</div>
              {Object.entries(rp.principles).map(([k, v]) => (
                <div key={k} style={{ marginTop: 8 }}>
                  <div className="row" style={{ justifyContent: "space-between", fontSize: 12.5 }}><span>{k}</span><span className="mono">{v}%</span></div>
                  <Bar pct={v} tone={v < 85 ? "warn" : "good"} />
                </div>
              ))}
              <p className="muted" style={{ fontSize: 12.5, margin: "12px 0 0" }}>Select any node to see its owner, CDEs and controls.</p>
            </>
          )}
        </div></section>
      </div>
      {impact && (
        <Modal title="Impact analysis" onClose={() => setImpact(null)}>
          <p className="muted" style={{ margin: 0 }}>A schema or logic change at {impact.node} would affect:</p>
          <ul style={{ margin: 0, paddingLeft: 18 }}>{impact.downstream.length ? impact.downstream.map((d) => <li key={d}>{d}</li>) : <li>Nothing downstream</li>}</ul>
          {impact.otherReports.length > 0 && <p style={{ margin: 0 }}><b>Also feeds:</b> {impact.otherReports.join(", ")}</p>}
        </Modal>
      )}
      {pack && (
        <Modal title={`Evidence pack ${pack.id}`} onClose={() => setPack(null)}>
          <pre>{pack.text}</pre>
          <button className="btn primary" onClick={() => copyText(pack.text, toast)}>Copy text</button>
        </Modal>
      )}
    </>
  );
}
