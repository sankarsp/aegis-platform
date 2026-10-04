"""Evidence packs: a plain-text summary plus a SHA-256 fingerprint of the content and the audit chain head."""

import hashlib
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import governance as gov
from .models import AuditEvent, Cde, LineageEdge, Report


def build_evidence_pack(db: Session, rp: Report, user: str) -> dict:
    edges = db.scalars(select(LineageEdge).where(LineageEdge.report_id == rp.id)).all()
    gate = gov.report_gate(db, rp)
    head = db.scalar(select(AuditEvent).order_by(AuditEvent.id.desc()).limit(1))
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    manual = [f"{e.source} → {e.target} ({e.kind}{', ' + e.signed_by if e.signed_by else ''})" for e in edges if e.kind != "auto"]
    lines = [
        "AEGIS EVIDENCE PACK",
        f"Report:        {rp.name}",
        f"Regulation:    {rp.regulation}",
        f"Generated:     {now} by {user}",
        "",
        f"Lineage:       {len(edges)} hops, {gov.lineage_completeness(db, rp.id)}% verified",
        f"Manual hops:   {'; '.join(manual) or 'none'}",
        f"Quality gate:  {'HELD (breach on ' + ', '.join(gate['breached_cdes']) + ')' if gate['held'] else 'CLEAR'}",
        "",
        "CDEs:",
    ]
    for cid in rp.cde_ids:
        c = db.get(Cde, cid)
        q = gov.cde_quality(db, cid)
        lines.append(f"  {cid:<28} owner {(c.owner or 'NONE'):<15} DQ {q if q is not None else 100:.2f}%  attested {c.attested}")
    lines += ["", "BCBS 239 coverage:"] + [f"  {k:<32}{v}%" for k, v in rp.principles.items()]
    lines += ["", f"Audit chain head: {head.hash if head else 'empty'}"]
    text = "\n".join(lines)
    digest = hashlib.sha256(text.encode()).hexdigest()
    return {"id": "EV-" + digest[:12].upper(), "sha256": digest, "text": text}
