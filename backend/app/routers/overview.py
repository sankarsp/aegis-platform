from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import audit as audit_log
from .. import governance as gov
from .. import serializers as ser
from ..auth import User, current_user
from ..db import get_db
from ..models import AiModel, AuditEvent, Campaign, Cde, DqRule, Issue, LineageEdge, LineageNode, Report, ReviewItem

router = APIRouter(prefix="/api", tags=["overview"])

# Daily average quality for the last 30 days, until the history table is populated by the scheduler.
QUALITY_HISTORY = [
    96.1,
    96.2,
    96.0,
    96.3,
    96.4,
    96.4,
    96.2,
    96.5,
    96.6,
    96.5,
    96.7,
    96.8,
    96.6,
    96.3,
    95.9,
    95.6,
    95.4,
    95.5,
    95.7,
    95.6,
    95.8,
    96.0,
    96.1,
    96.0,
    96.2,
    96.1,
    96.3,
    96.2,
    96.4,
]


@router.get("/overview")
def overview(db: Session = Depends(get_db)):
    cdes = db.scalars(select(Cde)).all()
    quals = [gov.cde_quality(db, c.id) or 100.0 for c in cdes]
    issues = [i for i in db.scalars(select(Issue)) if i.status != "Closed"]
    camps = db.scalars(select(Campaign)).all()
    items = db.scalars(select(ReviewItem)).all()
    total = sum(c.total for c in camps)
    done = sum(c.others_done for c in camps) + sum(1 for i in items if i.decision)
    models = db.scalars(select(AiModel)).all()

    attention = []
    for r in db.scalars(select(DqRule)):
        if gov.rule_status(r) == "breach":
            attention.append(
                {
                    "level": "crit",
                    "title": f"{r.id} breached on {r.cde_id}",
                    "detail": f"{r.name}: {r.last_value}% against {r.threshold}% threshold",
                    "go": "/quality",
                }
            )
    for c in cdes:
        if not c.owner:
            attention.append(
                {
                    "level": "crit",
                    "title": f"{c.id} has no owner",
                    "detail": f"{c.former_owner} left the firm; reassign in the catalog",
                    "go": "/catalog",
                }
            )
    for e in db.scalars(select(LineageEdge).where(LineageEdge.kind == "manual")):
        n, rp = db.get(LineageNode, e.source), db.get(Report, e.report_id)
        attention.append(
            {
                "level": "warn",
                "title": f"Unverified manual hop in {rp.name}",
                "detail": f"{n.label} ({n.sub}) needs steward sign-off",
                "go": f"/lineage/{rp.id}",
            }
        )
    for m in models:
        for a in gov.model_alerts(db, m):
            if a["level"] != "info":
                attention.append(
                    {"level": a["level"], "title": f"{m.name} {m.version}", "detail": a["text"], "go": f"/ai/{m.id}"}
                )
    open_reviews = sum(1 for i in items if not i.decision)
    if open_reviews:
        attention.append(
            {
                "level": "info",
                "title": f"{open_reviews} reviews waiting for you",
                "detail": "Recertification campaigns are open",
                "go": "/recert",
            }
        )

    avg_q = round(sum(quals) / len(quals), 1)
    intact, _ = audit_log.verify_chain(db)
    return {
        "kpis": {
            "lineageCoverage": round(sum(c.lineage_pct for c in cdes) / len(cdes)),
            "dataQuality": avg_q,
            "cdesOwned": sum(1 for c in cdes if c.owner),
            "cdesTotal": len(cdes),
            "recertDone": done,
            "recertTotal": total,
            "openIssues": len(issues),
            "criticalIssues": sum(1 for i in issues if i.severity == "Critical"),
            "openReviews": open_reviews,
            "models": len(models),
            "modelsWithAlerts": sum(1 for m in models if any(a["level"] != "info" for a in gov.model_alerts(db, m))),
        },
        "qualityTrend": QUALITY_HISTORY + [avg_q],
        "attention": attention,
        "reports": [
            {
                "id": r.id,
                "name": r.name,
                "regulation": r.regulation,
                "cadence": r.cadence,
                "gate": gov.report_gate(db, r),
                "completeness": gov.lineage_completeness(db, r.id),
            }
            for r in db.scalars(select(Report).order_by(Report.name))
        ],
        "recentActivity": [ser.audit_event(e) for e in db.scalars(select(AuditEvent).order_by(AuditEvent.id.desc()).limit(6))],
        "auditChainIntact": intact,
    }


@router.get("/audit")
def audit_events(limit: int = 200, db: Session = Depends(get_db)):
    intact, broken = audit_log.verify_chain(db)
    rows = db.scalars(select(AuditEvent).order_by(AuditEvent.id.desc()).limit(limit))
    return {"intact": intact, "firstBrokenId": broken, "events": [ser.audit_event(e) for e in rows]}


@router.get("/me")
def me(user: User = Depends(current_user)):
    return {"name": user.name, "email": user.id, "roles": sorted(user.roles)}
