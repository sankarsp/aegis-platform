from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import audit
from .. import governance as gov
from .. import serializers as ser
from ..auth import User, current_user, require
from ..db import get_db
from ..evidence import build_evidence_pack
from ..models import Cde, LineageEdge, LineageNode, Report

router = APIRouter(prefix="/api/reports", tags=["lineage"])


def _report(db: Session, report_id: str) -> Report:
    rp = db.get(Report, report_id)
    if not rp:
        raise HTTPException(404, f"No report with id '{report_id}'.")
    return rp


@router.get("")
def list_reports(db: Session = Depends(get_db)):
    return [
        {
            "id": r.id,
            "name": r.name,
            "regulation": r.regulation,
            "cadence": r.cadence,
            "owner": r.owner,
            "gate": gov.report_gate(db, r),
            "completeness": gov.lineage_completeness(db, r.id),
        }
        for r in db.scalars(select(Report).order_by(Report.name))
    ]


@router.get("/{report_id}")
def get_report(report_id: str, db: Session = Depends(get_db)):
    rp = _report(db, report_id)
    nodes = db.scalars(select(LineageNode).where(LineageNode.report_id == rp.id)).all()
    edges = db.scalars(select(LineageEdge).where(LineageEdge.report_id == rp.id)).all()

    def node_status(n: LineageNode) -> str:
        if not n.cde_ids:
            return "none"
        sts = [gov.cde_status(db, c) for c in n.cde_ids]
        return "breach" if "breach" in sts else ("warn" if "warn" in sts else "pass")

    return {
        "id": rp.id,
        "name": rp.name,
        "regulation": rp.regulation,
        "cadence": rp.cadence,
        "owner": rp.owner,
        "principles": rp.principles,
        "gate": gov.report_gate(db, rp),
        "completeness": gov.lineage_completeness(db, rp.id),
        "cdes": [ser.cde(db, db.get(Cde, c)) for c in rp.cde_ids],
        "nodes": [
            {
                "id": n.id,
                "label": n.label,
                "sub": n.sub,
                "col": n.col,
                "row": n.row,
                "isReport": n.is_report,
                "isEuc": n.is_euc,
                "owner": n.owner,
                "cdeIds": n.cde_ids,
                "controls": n.controls,
                "status": node_status(n),
            }
            for n in nodes
        ],
        "edges": [{"id": e.id, "source": e.source, "target": e.target, "kind": e.kind, "signedBy": e.signed_by} for e in edges],
    }


@router.post("/{report_id}/edges/{edge_id}/signoff")
def sign_off_edge(report_id: str, edge_id: int, db: Session = Depends(get_db), user: User = Depends(require("steward"))):
    rp = _report(db, report_id)
    e = db.get(LineageEdge, edge_id)
    if not e or e.report_id != rp.id:
        raise HTTPException(404, "That lineage hop is not part of this report.")
    if e.kind != "manual":
        raise HTTPException(409, "Only unverified manual hops need a sign-off.")
    e.kind, e.signed_by = "signed", user.label
    src = db.get(LineageNode, e.source)
    for c in src.cde_ids:
        cde = db.get(Cde, c)
        cde.lineage_pct = min(100, cde.lineage_pct + 8)
    audit.record(db, user, "Signed off manual lineage hop", f"{src.sub} → {rp.name}")
    db.commit()
    return {"completeness": gov.lineage_completeness(db, rp.id)}


@router.get("/{report_id}/nodes/{node_id}/impact")
def impact(report_id: str, node_id: str, db: Session = Depends(get_db)):
    """Everything downstream of a node in this report, plus other reports that read the same system."""
    rp = _report(db, report_id)
    edges = db.scalars(select(LineageEdge).where(LineageEdge.report_id == rp.id)).all()
    me = db.get(LineageNode, node_id)
    if not me or me.report_id != rp.id:
        raise HTTPException(404, "That node is not part of this report.")
    seen, stack = set(), [node_id]
    while stack:
        cur = stack.pop()
        for e in edges:
            if e.source == cur and e.target not in seen:
                seen.add(e.target)
                stack.append(e.target)
    downstream = [f"{n.label} ({n.sub})" for n in db.scalars(select(LineageNode).where(LineageNode.id.in_(seen)))]
    others = sorted(
        {
            db.get(Report, n.report_id).name
            for n in db.scalars(select(LineageNode).where(LineageNode.label == me.label, LineageNode.report_id != rp.id))
        }
    )
    return {"node": me.label, "downstream": downstream, "otherReports": others}


@router.post("/{report_id}/evidence-pack")
def evidence_pack(report_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    rp = _report(db, report_id)
    pack = build_evidence_pack(db, rp, user.label)
    audit.record(db, user, f"Generated evidence pack {pack['id']}", rp.name)
    db.commit()
    return pack
