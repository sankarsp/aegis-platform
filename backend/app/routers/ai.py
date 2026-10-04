"""AI governance: model inventory, monitoring, fairness, generative AI evaluations, approvals and kill switch."""

import random
import re
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import audit
from .. import governance as gov
from .. import serializers as ser
from ..auth import User, require
from ..db import get_db
from ..models import AiModel, Task

router = APIRouter(prefix="/api/ai/models", tags=["ai governance"])


def _model(db: Session, model_id: str) -> AiModel:
    m = db.get(AiModel, model_id)
    if not m:
        raise HTTPException(404, f"No model with id '{model_id}'.")
    return m


def _not_paused(m: AiModel) -> None:
    if m.stage.startswith("Paused"):
        raise HTTPException(409, "This model is paused. Resume it before changing its version or approvals.")


@router.get("")
def list_models(db: Session = Depends(get_db)):
    return [ser.model(db, m) for m in db.scalars(select(AiModel).order_by(AiModel.id))]


@router.get("/{model_id}")
def get_model(model_id: str, db: Session = Depends(get_db)):
    return ser.model(db, _model(db, model_id))


@router.post("/{model_id}/fairness-test")
def fairness_test(model_id: str, db: Session = Depends(get_db), user: User = Depends(require("steward"))):
    """Recomputes adverse impact ratios. The MVP simulates the scoring job; production reads the decision log."""
    m = _model(db, model_id)
    if not m.fairness:
        raise HTTPException(409, "This model has no fair lending test configured.")
    m.fairness = [{**f, "value": round(max(0.6, min(1.1, f["value"] + (random.random() - 0.5) * 0.03)), 2)} for f in m.fairness]
    audit.record(db, user, "Ran fairness test", f"{m.name} {m.version}")
    db.commit()
    return ser.model(db, m)


@router.post("/{model_id}/mitigate")
def mitigate(model_id: str, db: Session = Depends(get_db), user: User = Depends(require("steward"))):
    """Records a mitigated retrain as a new version, which must go back through approval."""
    m = _model(db, model_id)
    _not_paused(m)
    if not m.fairness or all(f["value"] >= gov.FOUR_FIFTHS for f in m.fairness):
        raise HTTPException(409, "No group is below the four-fifths threshold.")
    m.fairness = [{**f, "value": round(f["value"] + 0.08, 2) if f["value"] < 0.85 else f["value"]} for f in m.fairness]
    if m.performance:
        m.performance = {**m.performance, "value": round(m.performance["value"] - 0.004, 3)}
    m.version = re.sub(r"(\d+)$", lambda x: str(int(x.group(1)) + 1), m.version)
    m.approvals = [
        {"step": a["step"], "approved": i == 0, **({"by": user.label} if i == 0 else {})} for i, a in enumerate(m.approvals)
    ]
    m.stage, m.validated = "Awaiting approval", gov.today()
    audit.record(db, user, "Applied reweighting mitigation; new version needs approval", f"{m.name} {m.version}")
    db.commit()
    return ser.model(db, m)


@router.post("/{model_id}/evaluate")
def evaluate(model_id: str, db: Session = Depends(get_db), user: User = Depends(require("steward"))):
    """Runs the generative AI evaluation suite (simulated scores in the MVP)."""
    m = _model(db, model_id)
    if not m.llm_evals:
        raise HTTPException(409, "This model has no generative AI evaluation suite.")
    m.llm_evals = [
        {
            **e,
            "value": e["value"]
            if e["target"] >= 100
            else round(max(90, min(100, e["value"] + (random.random() - 0.4) * 0.8)), 1),
        }
        for e in m.llm_evals
    ]
    audit.record(db, user, "Ran generative AI evaluation suite", f"{m.name} {m.version}")
    db.commit()
    return ser.model(db, m)


@router.post("/{model_id}/approve")
def approve_next(model_id: str, db: Session = Depends(get_db), user: User = Depends(require("approver"))):
    """Records the next approval step. Segregation of duties: one person may sign only one step per version."""
    m = _model(db, model_id)
    _not_paused(m)
    pending = [a for a in m.approvals if not a["approved"]]
    if not pending:
        raise HTTPException(409, "Every approval step is already complete.")
    if any(a.get("by") == user.label for a in m.approvals if a["approved"]):
        raise HTTPException(403, "You already approved a step for this version. Another approver must sign the next step.")
    step = pending[0]["step"]
    m.approvals = [{**a, "approved": True, "by": user.label} if a["step"] == step else a for a in m.approvals]
    if all(a["approved"] for a in m.approvals):
        m.stage = "Approved for pilot" if m.stage == "Awaiting approval" and m.tier == "High" and m.llm_evals else "Production"
    audit.record(db, user, f"Recorded approval: {step}", f"{m.name} {m.version}")
    db.commit()
    return ser.model(db, m)


@router.post("/{model_id}/pause")
def pause(model_id: str, db: Session = Depends(get_db), user: User = Depends(require("approver", "admin"))):
    m = _model(db, model_id)
    if m.stage.startswith("Paused"):
        m.stage, m.prev_stage = m.prev_stage or "Production", None
        action = "Resumed model"
    else:
        m.prev_stage, m.stage = m.stage, "Paused, fallback active"
        action = "Paused model; rules-based fallback active"
    audit.record(db, user, action, f"{m.name} {m.version}")
    db.commit()
    return ser.model(db, m)


@router.post("/{model_id}/revalidate")
def revalidate(model_id: str, db: Session = Depends(get_db), user: User = Depends(require("steward"))):
    m = _model(db, model_id)
    m.next_validation = f"Requested {gov.today()}"
    db.add(
        Task(
            title=f"Revalidate {m.name} {m.version}",
            assignee=m.validator,
            due=(date.today() + timedelta(days=30)).isoformat(),
            source=f"Model {m.id}",
        )
    )
    audit.record(db, user, "Requested revalidation", f"{m.name} {m.version}")
    db.commit()
    return ser.model(db, m)
