from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import audit
from .. import serializers as ser
from ..auth import User, current_user, require
from ..db import get_db
from ..models import Campaign, ReviewItem, Task

router = APIRouter(prefix="/api/recert", tags=["recertification"])


class DecisionIn(BaseModel):
    keep: bool
    note: str = Field(default="", max_length=2000)


def _decided(db: Session, campaign_id: str) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(ReviewItem)
            .where(ReviewItem.campaign_id == campaign_id, ReviewItem.decision.is_not(None))
        )
        or 0
    )


@router.get("/campaigns")
def campaigns(db: Session = Depends(get_db)):
    return [ser.campaign(c, _decided(db, c.id)) for c in db.scalars(select(Campaign).order_by(Campaign.due))]


@router.get("/inbox")
def inbox(db: Session = Depends(get_db), user: User = Depends(current_user)):
    rows = db.scalars(select(ReviewItem).where(ReviewItem.reviewer == user.id)).all()
    return [ser.item(i) for i in rows]


@router.post("/items/{item_id}/decision")
def decide(item_id: str, body: DecisionIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    i = db.get(ReviewItem, item_id)
    if not i:
        raise HTTPException(404, "No review item with that id.")
    if i.reviewer != user.id:
        raise HTTPException(403, f"This item is assigned to {i.reviewer}.")
    if i.decision:
        raise HTTPException(409, "This item already has a decision.")
    if db.get(Campaign, i.campaign_id).sealed:
        raise HTTPException(409, "This campaign is sealed.")
    label = i.keep_label if body.keep else i.drop_label
    i.decision = {"keep": body.keep, "label": label, "by": user.label, "at": date.today().isoformat(), "note": body.note}
    if not body.keep:
        subject = i.title.split(" · ")[0]
        title = {"Access": f"Remove grant: {i.title}", "Lineage": f"Fix lineage gaps: {subject}"}.get(
            i.kind, f"Follow up: {subject}"
        )
        db.add(
            Task(
                title=title,
                assignee="Access control team" if i.kind == "Access" else "Lena Brandt",
                due=(date.today() + timedelta(days=7)).isoformat(),
                source=f"Review {i.id}",
            )
        )
    audit.record(db, user, f"{'Attested' if body.keep else 'Rejected'}: {label}", i.title)
    db.commit()
    return ser.item(i)


@router.post("/campaigns/{campaign_id}/seal")
def seal(campaign_id: str, db: Session = Depends(get_db), user: User = Depends(require("approver", "admin"))):
    c = db.get(Campaign, campaign_id)
    if not c:
        raise HTTPException(404, "No campaign with that id.")
    if c.sealed:
        raise HTTPException(409, "This campaign is already sealed.")
    if c.others_done + _decided(db, c.id) < c.total:
        raise HTTPException(409, "Every item needs a decision before the campaign can be sealed.")
    ev = audit.record(db, user, "Sealed campaign", c.name)
    c.sealed, c.evidence_id = True, "EV-" + ev.hash[:10].upper()
    db.commit()
    return ser.campaign(c, _decided(db, c.id))


@router.get("/tasks")
def tasks(db: Session = Depends(get_db)):
    return [ser.task(t) for t in db.scalars(select(Task).order_by(Task.id.desc()))]
