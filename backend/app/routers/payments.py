"""Payment rails: ACH, wires, Fedwire, Swift, RTP, FedNow and SEPA Instant, each tied to its data, rules and models."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import governance as gov
from .. import serializers as ser
from ..db import get_db
from ..models import AiModel, Cde, DqRule, Issue, PaymentRail, Report

router = APIRouter(prefix="/api/payments", tags=["payment rails"])

ORDER = ["ach", "wire", "fedwire", "swift", "rtp", "fednow", "sepa_inst"]


def _summary(db: Session, r: PaymentRail) -> dict:
    return {
        "id": r.id,
        "name": r.name,
        "category": r.category,
        "region": r.region,
        "operator": r.operator,
        "messageStandard": r.message_standard,
        "settlement": r.settlement,
        "availability": r.availability,
        "limit": r.txn_limit,
        "routesTo": r.routes_to,
        "metrics": r.metrics,
        **gov.rail_status(db, r),
    }


@router.get("/rails")
def rails(db: Session = Depends(get_db)):
    rows = db.scalars(select(PaymentRail)).all()
    rows.sort(key=lambda r: ORDER.index(r.id) if r.id in ORDER else len(ORDER))
    return [_summary(db, r) for r in rows]


@router.get("/rails/{rail_id}")
def rail(rail_id: str, db: Session = Depends(get_db)):
    r = db.get(PaymentRail, rail_id)
    if not r:
        raise HTTPException(404, f"No payment rail with id '{rail_id}'.")
    cdes = [ser.cde(db, c) for c in (db.get(Cde, cid) for cid in r.cde_ids) if c]
    rules = [ser.rule(x) for x in db.scalars(select(DqRule).where(DqRule.cde_id.in_(r.cde_ids)).order_by(DqRule.id))]
    issues = [ser.issue(i) for i in db.scalars(select(Issue).where(Issue.cde_id.in_(r.cde_ids), Issue.status != "Closed"))]
    models = []
    for mid in r.model_ids:
        m = db.get(AiModel, mid)
        if m:
            models.append(
                {
                    "id": m.id,
                    "name": m.name,
                    "version": m.version,
                    "tier": m.tier,
                    "stage": m.stage,
                    "alerts": [a for a in gov.model_alerts(db, m) if a["level"] != "info"],
                }
            )
    report = db.get(Report, r.report_id) if r.report_id else None
    return {
        **_summary(db, r),
        "description": r.description,
        "regulations": r.regulations,
        "changes": sorted(r.changes, key=lambda c: c["date"], reverse=True),
        "controls": r.controls,
        "cdes": cdes,
        "rules": rules,
        "issues": issues,
        "models": models,
        "report": {
            "id": report.id,
            "name": report.name,
            "gate": gov.report_gate(db, report),
            "completeness": gov.lineage_completeness(db, report.id),
        }
        if report
        else None,
    }
