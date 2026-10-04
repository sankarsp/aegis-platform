"""Data quality. Rules execute where the data lives; this MVP ships a simulated runner so the
console works without warehouse credentials. Swap in WarehouseRuleRunner (push-down SQL) for production."""

import random
from datetime import date, timedelta
from typing import Protocol

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import audit
from .. import governance as gov
from .. import serializers as ser
from ..auth import User, require
from ..db import get_db
from ..models import Cde, DqRule, Issue, Report

router = APIRouter(prefix="/api/quality", tags=["quality"])


class RuleRunner(Protocol):
    def run(self, rule: DqRule) -> float: ...


class SimulatedRuleRunner:
    """Moves each result a little, as daily data would. Rules with a 100% threshold rarely move."""

    def run(self, rule: DqRule) -> float:
        drift = 0.0 if (rule.threshold >= 100 and random.random() < 0.85) else (random.random() - 0.45) * 1.2
        return max(80.0, min(100.0, round(rule.last_value + drift, 2)))


runner: RuleRunner = SimulatedRuleRunner()


@router.get("/rules")
def rules(db: Session = Depends(get_db)):
    return [ser.rule(r) for r in db.scalars(select(DqRule).order_by(DqRule.id))]


@router.post("/run")
def run_all(db: Session = Depends(get_db), user: User = Depends(require("steward"))):
    opened = []
    for r in db.scalars(select(DqRule)):
        before = gov.rule_status(r)
        r.last_value = runner.run(r)
        if gov.rule_status(r) == "breach" and before != "breach":
            already = db.scalar(select(Issue).where(Issue.rule_id == r.id, Issue.status != "Closed"))
            if not already:
                n = len(db.scalars(select(Issue)).all())
                cde = db.get(Cde, r.cde_id)
                iss = Issue(
                    id=f"ISS-{2042 + n}",
                    rule_id=r.id,
                    cde_id=r.cde_id,
                    severity="High",
                    owner=cde.steward,
                    opened=date.today().isoformat(),
                    due=(date.today() + timedelta(days=7)).isoformat(),
                    status="New",
                    note=f"Opened automatically: {r.name} fell to {r.last_value}%.",
                )
                db.add(iss)
                opened.append(iss.id)
    audit.record(db, user, "Ran quality rules", "All CDEs")
    db.commit()
    return {"opened": opened}


@router.get("/issues")
def issues(db: Session = Depends(get_db)):
    rows = db.scalars(select(Issue)).all()
    return [ser.issue(i) for i in sorted(rows, key=lambda i: (i.status == "Closed", i.due))]


@router.post("/issues/{issue_id}/resolve")
def resolve(issue_id: str, db: Session = Depends(get_db), user: User = Depends(require("steward"))):
    i = db.get(Issue, issue_id)
    if not i:
        raise HTTPException(404, f"No issue with id '{issue_id}'.")
    if i.status == "Closed":
        raise HTTPException(409, "This issue is already resolved.")
    r = db.get(DqRule, i.rule_id)
    # Resolving re-runs the rule; in this MVP the fix is assumed to bring it just above threshold.
    if r and gov.rule_status(r) == "breach":
        r.last_value = min(100.0, r.threshold + 0.3)
    i.status = "Closed"
    audit.record(db, user, "Resolved issue; rule re-run passed", f"{i.id} · {i.cde_id}")
    db.commit()
    return ser.issue(i)


@router.get("/gates")
def gates(db: Session = Depends(get_db)):
    return [{"reportId": r.id, "name": r.name, **gov.report_gate(db, r)} for r in db.scalars(select(Report))]
