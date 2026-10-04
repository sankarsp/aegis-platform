import { useState } from "react";
import { api } from "../api";
import { Bar, Loading, PageHead, Pill, useAction, useLoad } from "../components/ui";
import type { Campaign, ReviewItem } from "../types";

function ReviewCard({ item, campaign, onDone }: { item: ReviewItem; campaign?: Campaign; onDone: () => void }) {
  const [note, setNote] = useState("");
  const { run, busy } = useAction();
  const d = item.decision;
  return (
    <div className={`review ${d ? "done" : ""}`}>
      <div className="row" style={{ justifyContent: "space-between" }}>
        <div className="row" style={{ gap: 8 }}><Pill tone="info">{item.kind}</Pill><span className="tag">{item.tag}</span><span className="muted" style={{ fontSize: 12 }}>{campaign?.name}</span></div>
        {d && <Pill tone={d.keep ? "good" : "warn"}>{d.label}</Pill>}
      </div>
      <div style={{ fontWeight: 600 }}>{item.title}</div>
      <ul>{item.context.map((c) => <li key={c}>{c}</li>)}</ul>
      {d ? (
        <div className="muted" style={{ fontSize: 12.5 }}>{d.at} by {d.by}{d.note && ` · “${d.note}”`}</div>
      ) : (
        <>
          <div className="rec"><b>Suggested:</b> {item.recommendation} <span className="muted">(advisory; your decision is final)</span></div>
          <textarea id={`note-${item.id}`} placeholder="Comment for the audit record (optional)" aria-label="Comment" value={note} onChange={(e) => setNote(e.target.value)} />
          <div className="row">
            <button className="btn primary" disabled={busy} onClick={() => run(() => api.decide(item.id, true, note), () => "Attested.", onDone)}>{item.keepLabel}</button>
            <button className="btn danger" disabled={busy} onClick={() => run(() => api.decide(item.id, false, note), () => "Recorded. A remediation task was created.", onDone)}>{item.dropLabel}</button>
          </div>
        </>
      )}
    </div>
  );
}

export default function Recert() {
  const camps = useLoad(api.campaigns);
  const inbox = useLoad(api.inbox);
  const tasks = useLoad(api.tasks);
  const { run, busy } = useAction();
  const refresh = () => { camps.reload(); inbox.reload(); tasks.reload(); };
  if (!camps.data || !inbox.data || !tasks.data) return <Loading error={camps.error || inbox.error || tasks.error} />;
  const open = inbox.data.filter((i) => !i.decision), done = inbox.data.filter((i) => i.decision);
  const byId = Object.fromEntries(camps.data.map((c) => [c.id, c]));
  return (
    <>
      <PageHead title="Review and recertification" intro="Scheduled, risk-based campaigns. Each item arrives with its context; access not re-approved by the deadline is revoked automatically." />
      <div className="kpis">{camps.data.map((c) => {
        const pct = Math.round((c.done / c.total) * 100);
        return (
          <div key={c.id} className="kpi">
            <span className="eyebrow">{c.type} · due {c.due}</span>
            <b style={{ fontSize: 14.5 }}>{c.name}</b>
            <div className="row" style={{ gap: 8 }}><div style={{ flex: 1 }}><Bar pct={pct} tone={pct === 100 ? "good" : ""} /></div><span className="mono">{c.done}/{c.total}</span></div>
            <span className="s">{c.sealed ? `Sealed · evidence ${c.evidenceId}` : pct === 100 ? "All items attested" : `${c.total - c.done} items outstanding`}</span>
            {c.sealed ? <Pill tone="good">Sealed</Pill> :
              <button className={`btn sm ${c.canSeal ? "primary" : ""}`} disabled={!c.canSeal || busy}
                onClick={() => run(() => api.seal(c.id), (r) => `Campaign sealed. Evidence ${r.evidenceId}.`, refresh)}>Seal campaign</button>}
          </div>
        );
      })}</div>
      <section className="panel">
        <header><h2>Your inbox</h2><span className="muted" style={{ fontSize: 12.5 }}>{open.length} to review · {done.length} done</span></header>
        {open.length ? open.map((i) => <ReviewCard key={i.id} item={i} campaign={byId[i.campaignId]} onDone={refresh} />)
          : <div className="body muted">Nothing waiting for you.</div>}
      </section>
      {tasks.data.length > 0 && (
        <section className="panel">
          <header><h2>Remediation tasks</h2></header>
          <div className="list">{tasks.data.map((t) => (
            <div key={t.id}><div><div className="t">{t.title}</div><div className="d">{t.assignee} · due {t.due} · from {t.source}</div></div><Pill tone="warn">{t.status}</Pill></div>
          ))}</div>
        </section>
      )}
      {done.length > 0 && (
        <section className="panel"><header><h2>Completed</h2></header>{done.map((i) => <ReviewCard key={i.id} item={i} campaign={byId[i.campaignId]} onDone={refresh} />)}</section>
      )}
    </>
  );
}
