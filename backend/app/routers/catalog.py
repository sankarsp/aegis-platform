from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import audit
from .. import governance as gov
from .. import serializers as ser
from ..auth import User, require
from ..db import get_db
from ..models import Asset, Cde, DqRule, GlossaryTerm, Issue
from ..vectorstore import get_store

router = APIRouter(prefix="/api/catalog", tags=["catalog"])


class OwnerIn(BaseModel):
    owner: str = Field(min_length=2, max_length=120)


@router.get("/assets")
def assets(q: str = "", db: Session = Depends(get_db)):
    rows = db.scalars(select(Asset).order_by(Asset.name)).all()
    if q:
        ql = q.lower()
        rows = [a for a in rows if ql in " ".join([a.name, a.domain, a.owner or "", a.term, *a.cde_ids]).lower()]
    return [ser.asset(db, a) for a in rows]


@router.post("/assets/{asset_id}/owner")
def assign_owner(asset_id: int, body: OwnerIn, db: Session = Depends(get_db), user: User = Depends(require("steward"))):
    a = db.get(Asset, asset_id)
    if not a:
        raise HTTPException(404, "No dataset with that id.")
    a.owner = body.owner
    for cid in a.cde_ids:  # orphaned CDEs in this dataset follow the dataset's new owner
        c = db.get(Cde, cid)
        if c and not c.owner:
            c.owner = body.owner
            c.attested = gov.today()
    audit.record(db, user, f"Assigned owner {body.owner}", a.name)
    gov.index_asset(db, a)
    db.commit()
    return ser.asset(db, a)


@router.get("/cdes")
def cdes(db: Session = Depends(get_db)):
    return [ser.cde(db, c) for c in db.scalars(select(Cde).order_by(Cde.id))]


@router.get("/glossary")
def glossary(db: Session = Depends(get_db)):
    return [ser.term(g) for g in db.scalars(select(GlossaryTerm).order_by(GlossaryTerm.term))]


@router.get("/glossary/similar")
def similar_terms(text: str, db: Session = Depends(get_db)):
    """Finds existing terms close to a proposed one, so stewards reuse definitions instead of duplicating them."""
    return [
        {"termId": int(h.ref_id), "term": h.title, "definition": h.body, "score": round(h.score, 3)}
        for h in get_store().search(db, text, k=3, kinds=["term"])
    ]


@router.post("/glossary/{term_id}/approve")
def approve_change(term_id: int, db: Session = Depends(get_db), user: User = Depends(require("steward", "admin"))):
    g = db.get(GlossaryTerm, term_id)
    if not g or not g.proposed_change:
        raise HTTPException(404, "There is no proposed change to approve for this term.")
    g.definition = g.proposed_definition or g.definition
    g.version = f"v{int(g.version.lstrip('v')) + 1}"
    g.status, g.proposed_change, g.proposed_definition = "Approved", None, None
    if g.term == "KYC status":  # the value set behind DQ-105 now includes the new status
        r = db.get(DqRule, "DQ-105")
        r.last_value = 97.6
        for i in db.scalars(select(Issue).where(Issue.rule_id == "DQ-105", Issue.status != "Closed")):
            i.status = "Closed"
    audit.record(db, user, f"Approved glossary change ({g.version})", g.term)
    gov.index_term(db, g)
    db.commit()
    return ser.term(g)
