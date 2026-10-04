import { useEffect, useState } from "react";
import { api } from "../api";
import { ClassTag, Loading, PageHead, Pill, useAction, useLoad } from "../components/ui";
import type { SimilarTerm } from "../types";

const PEOPLE = ["Priya Nair", "Daniel Okafor", "Aisha Rahman", "Kenji Watanabe", "Marco Diaz", "Lena Brandt", "Tom Becker", "Sara Lim", "Elena Rossi"];

function Datasets() {
  const [q, setQ] = useState(() => new URLSearchParams(location.search).get("q") ?? "");
  const [debounced, setDebounced] = useState(q);
  useEffect(() => { const t = setTimeout(() => setDebounced(q), 200); return () => clearTimeout(t); }, [q]);
  const { data, error, reload } = useLoad(() => api.assets(debounced), [debounced]);
  const [selId, setSelId] = useState<number | null>(null);
  const [owner, setOwner] = useState(PEOPLE[0]);
  const { run, busy } = useAction();
  if (!data) return <Loading error={error} />;
  const a = data.find((x) => x.id === selId);
  return (
    <div className="grid g-side">
      <section className="panel">
        <header>
          <input type="search" id="catalog-search" placeholder="Search datasets, owners, CDEs" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search catalog" />
          <span className="muted" style={{ fontSize: 12.5 }}>{data.length} datasets</span>
        </header>
        <div className="tbl"><table>
          <thead><tr><th>Dataset</th><th>Platform</th><th>Domain</th><th>Owner</th><th>Class</th><th>Status</th></tr></thead>
          <tbody>
            {data.map((x) => (
              <tr key={x.id} className={`click ${x.id === selId ? "sel" : ""}`} onClick={() => setSelId(x.id)}>
                <td className="mono">{x.name}</td><td>{x.platform}</td><td>{x.domain}</td>
                <td>{x.owner ?? <Pill tone="crit">No owner</Pill>}</td><td><ClassTag cls={x.classification} /></td>
                <td>{x.certified ? <Pill tone="good">Certified</Pill> : <Pill>Not certified</Pill>}</td>
              </tr>
            ))}
            {data.length === 0 && <tr><td colSpan={6} className="muted">No datasets match “{q}”.</td></tr>}
          </tbody>
        </table></div>
      </section>
      <section className="panel"><div className="body">
        {a ? (
          <>
            <div className="eyebrow">Dataset</div>
            <h2 className="mono" style={{ fontSize: 14, margin: "4px 0 10px", overflowWrap: "anywhere" }}>{a.name}</h2>
            {!a.owner && (
              <div className="stripe crit" style={{ marginBottom: 12 }}>
                <b>Orphaned asset</b>
                <div className="muted" style={{ fontSize: 12.5 }}>{a.formerOwner} left the firm (HR feed). Assign a new owner.</div>
                <div className="row" style={{ marginTop: 8 }}>
                  <select id="new-owner" aria-label="New owner" value={owner} onChange={(e) => setOwner(e.target.value)}>{PEOPLE.map((p) => <option key={p}>{p}</option>)}</select>
                  <button className="btn primary sm" disabled={busy} onClick={() => run(() => api.assignOwner(a.id, owner), () => `${owner} is now the owner.`, reload)}>Assign owner</button>
                </div>
              </div>
            )}
            <dl className="kv">
              <dt>Owner</dt><dd>{a.owner ?? "None"}</dd><dt>Steward</dt><dd>{a.steward}</dd><dt>Platform</dt><dd>{a.platform}</dd>
              <dt>Glossary</dt><dd>{a.term}</dd><dt>Class</dt><dd><ClassTag cls={a.classification} /></dd>
              <dt>CDEs</dt><dd className="mono">{a.cdeIds.join(", ") || "None"}</dd><dt>Usage</dt><dd>{a.usage}</dd>
            </dl>
            <div className="eyebrow" style={{ marginTop: 14 }}>Certification criteria</div>
            <ul style={{ margin: "6px 0 0", paddingLeft: 18, fontSize: 13 }}>
              <li>{a.owner ? "Owner assigned" : <b>Missing owner</b>}</li>
              <li>{a.qualityOk ? "Quality within thresholds" : <b>Quality breach on a CDE</b>}</li>
              <li>{a.manualLineage ? <b>EUC: manual lineage</b> : "Automated lineage"}</li>
            </ul>
          </>
        ) : <p className="muted" style={{ margin: 0 }}>Select a dataset to see its owner, glossary term, CDEs and certification status.</p>}
      </div></section>
    </div>
  );
}

function Glossary() {
  const { data, error, reload } = useLoad(api.glossary);
  const { run, busy } = useAction();
  const [draft, setDraft] = useState("");
  const [similar, setSimilar] = useState<SimilarTerm[] | null>(null);
  if (!data) return <Loading error={error} />;
  return (
    <>
      <section className="panel">
        <header><h2>Propose a new term</h2><span className="muted" style={{ fontSize: 12.5 }}>Aegis checks the vector index for existing terms first</span></header>
        <div className="body grid" style={{ gap: 10 }}>
          <div className="searchbar">
            <input type="search" id="term-draft" placeholder="Describe the term, for example: money we owe the partner bank each day" value={draft} onChange={(e) => setDraft(e.target.value)} aria-label="Proposed term" />
            <button className="btn primary" disabled={busy || draft.trim().length < 3} onClick={() => run(() => api.similarTerms(draft), setSimilar)}>Check for duplicates</button>
          </div>
          {similar && (similar.length ? similar.map((s) => (
            <div key={s.termId} className="stripe info"><b>{s.term}</b> <span className="mono muted">similarity {s.score.toFixed(2)}</span><div style={{ fontSize: 13 }}>{s.definition}</div></div>
          )) : <span className="muted">No similar terms found.</span>)}
        </div>
      </section>
      <section className="panel"><div className="list">{data.map((g) => (
        <div key={g.id}>
          <div style={{ minWidth: 0 }}>
            <div className="row" style={{ gap: 8 }}><span className="t">{g.term}</span><span className="mono muted">{g.version}</span><Pill tone={g.status === "Approved" ? "good" : "warn"}>{g.status}</Pill></div>
            <div style={{ marginTop: 4, maxWidth: "70ch" }}>{g.definition}</div>
            {g.proposedChange && <div className="stripe warn" style={{ marginTop: 8, fontSize: 13 }}>Proposed change: {g.proposedChange}</div>}
            <div className="d" style={{ marginTop: 4 }}>Owner: {g.owner}</div>
          </div>
          {g.proposedChange && <button className="btn primary sm" disabled={busy} onClick={() => run(() => api.approveTerm(g.id), () => "Approved. Linked quality rules were re-run.", reload)}>Approve change</button>}
        </div>
      ))}</div></section>
    </>
  );
}

export default function Catalog() {
  const [view, setView] = useState<"datasets" | "glossary">("datasets");
  return (
    <>
      <PageHead title="Catalog and ownership"
        intro="One catalog of record for datasets, business terms, owners and stewards. Owner changes from the HR feed raise reassignment tasks automatically."
        actions={<div className="seg" role="group" aria-label="Catalog view">
          <button aria-pressed={view === "datasets"} onClick={() => setView("datasets")}>Datasets</button>
          <button aria-pressed={view === "glossary"} onClick={() => setView("glossary")}>Glossary</button>
        </div>} />
      {view === "datasets" ? <Datasets /> : <Glossary />}
    </>
  );
}
