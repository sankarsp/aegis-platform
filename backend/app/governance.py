"""Governance rules shared by the API: quality status, report gates, lineage completeness, model alerts, indexing."""

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import AiModel, Asset, Cde, DqRule, GlossaryTerm, LineageEdge, Policy, Report, Scan
from .vectorstore import get_store

FOUR_FIFTHS = 0.80
PSI_WATCH, PSI_ALERT = 0.10, 0.25


def today() -> str:
    return date.today().isoformat()


def rule_status(r: DqRule) -> str:
    if r.last_value >= r.threshold:
        return "pass"
    return "warn" if r.threshold - r.last_value <= 1.5 else "breach"


def cde_status(db: Session, cde_id: str) -> str:
    worst = "pass"
    for r in db.scalars(select(DqRule).where(DqRule.cde_id == cde_id)):
        s = rule_status(r)
        if s == "breach":
            return "breach"
        if s == "warn":
            worst = "warn"
    return worst


def cde_quality(db: Session, cde_id: str) -> float | None:
    vals = [r.last_value for r in db.scalars(select(DqRule).where(DqRule.cde_id == cde_id))]
    return min(vals) if vals else None


def report_gate(db: Session, rp: Report) -> dict:
    held = [c for c in rp.cde_ids if cde_status(db, c) == "breach"]
    return {"held": bool(held), "breached_cdes": held}


def lineage_completeness(db: Session, report_id: str) -> int:
    edges = db.scalars(select(LineageEdge).where(LineageEdge.report_id == report_id)).all()
    if not edges:
        return 100
    return round(sum(e.kind != "manual" for e in edges) / len(edges) * 100)


def model_alerts(db: Session, m: AiModel) -> list[dict]:
    alerts: list[dict] = []
    for f in m.fairness or []:
        if f["value"] < FOUR_FIFTHS:
            alerts.append({"level": "crit", "text": f"Fairness: {f['group']} adverse impact ratio {f['value']:.2f}"})
    if m.psi is not None and m.psi >= PSI_ALERT:
        alerts.append({"level": "crit", "text": f"Drift: PSI {m.psi:.2f} above {PSI_ALERT}"})
    paused = m.stage.startswith("Paused")
    if m.next_validation[:1].isdigit() and m.next_validation < today() and not paused:
        alerts.append({"level": "warn", "text": f"Validation overdue since {m.next_validation}"})
    for e in m.llm_evals or []:
        if e["value"] < e["target"]:
            alerts.append({"level": "warn", "text": f"{e['name']} {e['value']}% vs {e['target']}% target"})
    for c in m.data_cdes:
        if cde_status(db, c) == "breach":
            alerts.append({"level": "warn", "text": f"Input data quality breach on {c}"})
    pending = [a["step"] for a in m.approvals if not a["approved"]]
    if pending and m.stage != "Production":
        alerts.append({"level": "info", "text": f"Approval pending: {pending[0]}"})
    return alerts


def index_asset(db: Session, a: Asset) -> None:
    get_store().upsert(
        db,
        "dataset",
        a.name,
        a.name,
        f"{a.platform} dataset in {a.domain}. Business term: {a.term}. Classification: {a.classification}. "
        f"Owner: {a.owner or 'none'}. Steward: {a.steward}. CDEs: {', '.join(a.cde_ids)}.",
        {"owner": a.owner, "classification": a.classification},
    )


def index_cde(db: Session, c: Cde) -> None:
    get_store().upsert(
        db,
        "cde",
        c.id,
        f"{c.name} ({c.id})",
        f"Critical data element in {c.domain}. Classification {c.classification}. Owner {c.owner or 'none'}.",
        {"domain": c.domain},
    )


def index_term(db: Session, g: GlossaryTerm) -> None:
    get_store().upsert(db, "term", str(g.id), g.term, g.definition, {"status": g.status, "owner": g.owner})


def index_policy(db: Session, p: Policy) -> None:
    get_store().upsert(db, "policy", p.id, p.name, f"{p.rule}. Scope: {p.scope}. Mode: {p.mode}.", {"mode": p.mode})


def index_model(db: Session, m: AiModel) -> None:
    get_store().upsert(
        db,
        "model",
        m.id,
        f"{m.name} {m.version}",
        f"{m.use}. {m.model_type} from {m.source}. Risk tier {m.tier}. Obligations: {'; '.join(m.regulations)}. "
        f"Controls: {'; '.join(m.controls)}.",
        {"tier": m.tier, "stage": m.stage},
    )


def index_scan(db: Session, s: Scan) -> None:
    """Only steward-confirmed labels are used to suggest labels for new columns."""
    if s.status == "Confirmed":
        get_store().upsert(db, "labelled_column", s.id, s.column_name, f"{s.column_name} labelled {s.label}", {"label": s.label})


def index_report(db: Session, rp: Report) -> None:
    get_store().upsert(
        db, "report", rp.id, rp.name, f"Regulatory report for {rp.regulation}. Cadence {rp.cadence}. Owner {rp.owner}."
    )


def reindex(db: Session) -> int:
    """Embed every governed object into the vector store. Safe to re-run; used at first start and by admins."""
    for a in db.scalars(select(Asset)):
        index_asset(db, a)
    for c in db.scalars(select(Cde)):
        index_cde(db, c)
    for g in db.scalars(select(GlossaryTerm)):
        index_term(db, g)
    for p in db.scalars(select(Policy)):
        index_policy(db, p)
    for m in db.scalars(select(AiModel)):
        index_model(db, m)
    for s in db.scalars(select(Scan)):
        index_scan(db, s)
    for rp in db.scalars(select(Report)):
        index_report(db, rp)
    db.commit()
    return get_store().count(db)
