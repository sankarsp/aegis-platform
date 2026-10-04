import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { PageHead, Pill, useAction } from "../components/ui";
import type { AskResult } from "../types";

const KIND_LABEL: Record<string, string> = { dataset: "Dataset", cde: "CDE", term: "Glossary term", policy: "Policy", model: "AI model", report: "Report" };

function linkFor(kind: string, refId: string, title: string) {
  if (kind === "report") return `/lineage/${refId}`;
  if (kind === "model") return `/ai/${refId}`;
  if (kind === "policy") return "/access";
  if (kind === "term") return "/catalog";
  return `/catalog?q=${encodeURIComponent(kind === "cde" ? refId : title)}`;
}

const EXAMPLES = ["Which models make credit decisions and how are they tested for fairness?", "Where does customer personal data live?", "What feeds the sponsor bank reconciliation?"];

export default function Search() {
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<AskResult | null>(null);
  const { run, busy } = useAction();
  const ask = (q: string) => { setQuestion(q); run(() => api.ask(q), setResult); };
  return (
    <>
      <PageHead title="Ask Aegis" intro="Semantic search across datasets, CDEs, glossary terms, policies, reports and model cards, served from the vector index." />
      <section className="panel"><div className="body grid" style={{ gap: 12 }}>
        <form className="searchbar" onSubmit={(e) => { e.preventDefault(); if (question.trim().length >= 3) ask(question); }}>
          <input type="search" id="ask" value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="Ask about your data or AI governance" aria-label="Question" />
          <button className="btn primary" type="submit" disabled={busy || question.trim().length < 3}>{busy ? "Searching…" : "Ask"}</button>
        </form>
        <div className="row">{EXAMPLES.map((e) => <button key={e} className="btn sm" onClick={() => ask(e)}>{e}</button>)}</div>
      </div></section>
      {result && (
        <>
          {result.answer && (
            <section className="panel"><header><h2>Answer</h2><span className="muted" style={{ fontSize: 12.5 }}>Drafted from the records below; check the sources</span></header>
              <div className="body answer">{result.answer}</div></section>
          )}
          <section className="panel">
            <header><h2>Most relevant records</h2><span className="muted" style={{ fontSize: 12.5 }}>{result.sources.length} results</span></header>
            <div className="list">{result.sources.map((h, i) => (
              <div key={`${h.kind}-${h.refId}`}>
                <div style={{ minWidth: 0 }}>
                  <div className="row" style={{ gap: 8 }}><span className="mono muted">[{i + 1}]</span><Pill tone="info">{KIND_LABEL[h.kind] ?? h.kind}</Pill><Link className="t" to={linkFor(h.kind, h.refId, h.title)}>{h.title}</Link></div>
                  <div className="d" style={{ marginTop: 4 }}>{h.body}</div>
                </div>
                <span className="mono muted">{h.score.toFixed(2)}</span>
              </div>
            ))}</div>
          </section>
        </>
      )}
    </>
  );
}
