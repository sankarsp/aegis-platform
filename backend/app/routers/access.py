from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import audit
from .. import governance as gov
from .. import serializers as ser
from ..auth import User, require
from ..db import get_db
from ..models import Policy, Scan
from ..vectorstore import get_store

router = APIRouter(prefix="/api/access", tags=["access"])


class ScanDecision(BaseModel):
    status: Literal["Confirmed", "Rejected"]


class SuggestIn(BaseModel):
    column: str = Field(min_length=2, max_length=200)
    description: str = ""


@router.get("/scans")
def scans(db: Session = Depends(get_db)):
    return [ser.scan(s) for s in db.scalars(select(Scan).order_by(Scan.id))]


@router.post("/scans/{scan_id}")
def decide_scan(scan_id: str, body: ScanDecision, db: Session = Depends(get_db), user: User = Depends(require("steward"))):
    s = db.get(Scan, scan_id)
    if not s:
        raise HTTPException(404, "No scan result with that id.")
    if s.status != "Proposed":
        raise HTTPException(409, f"This label was already {s.status.lower()}.")
    s.status = body.status
    audit.record(db, user, f"{body.status} label {s.label}", s.column_name)
    gov.index_scan(db, s)  # confirmed labels teach the label suggestions below
    db.commit()
    return ser.scan(s)


@router.post("/suggest-classification")
def suggest(body: SuggestIn, db: Session = Depends(get_db)):
    """Suggests a sensitivity label for a new column from the most similar steward-confirmed columns."""
    hits = get_store().search(db, f"{body.column} {body.description}", k=3, kinds=["labelled_column"])
    if not hits:
        return {"suggestion": None, "neighbours": []}
    best = hits[0]
    return {
        "suggestion": best.meta.get("label"),
        "confidence": round(max(0.0, best.score), 3),
        "neighbours": [{"column": h.title, "label": h.meta.get("label"), "score": round(h.score, 3)} for h in hits],
        "note": "Advisory only. A steward confirms every label.",
    }


@router.get("/policies")
def policies(db: Session = Depends(get_db)):
    return [ser.policy(p) for p in db.scalars(select(Policy).order_by(Policy.id))]


@router.post("/policies/{policy_id}/toggle")
def toggle(policy_id: str, db: Session = Depends(get_db), user: User = Depends(require("admin"))):
    p = db.get(Policy, policy_id)
    if not p:
        raise HTTPException(404, "No policy with that id.")
    p.mode = "Monitor only" if p.mode == "Enforced" else "Enforced"
    audit.record(db, user, f"Set policy to {p.mode}", p.name)
    db.commit()
    return ser.policy(p)
