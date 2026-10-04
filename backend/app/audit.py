"""Hash-chained audit log."""

import hashlib
import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import advisory_lock
from .models import AuditEvent

GENESIS = "0" * 64
AUDIT_LOCK = 7301  # serialises appends so concurrent tasks never fork the chain


def _digest(prev_hash: str, ts: str, actor: str, action: str, obj: str) -> str:
    payload = json.dumps([prev_hash, ts, actor, action, obj], separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def record(db: Session, actor, action: str, obj: str, ts: str | None = None) -> AuditEvent:
    """Appends an event. `actor` is an auth.User or a system name such as "Aegis scheduler"."""
    actor = getattr(actor, "label", actor)
    with advisory_lock(db, AUDIT_LOCK):
        last = db.scalar(select(AuditEvent).order_by(AuditEvent.id.desc()).limit(1))
        prev = last.hash if last else GENESIS
        ts = ts or datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        ev = AuditEvent(ts=ts, actor=actor, action=action, object=obj, prev_hash=prev, hash=_digest(prev, ts, actor, action, obj))
        db.add(ev)
        db.flush()
    return ev


def verify_chain(db: Session) -> tuple[bool, int | None]:
    """Returns (intact, id of first broken event)."""
    prev = GENESIS
    for ev in db.scalars(select(AuditEvent).order_by(AuditEvent.id)):
        if ev.prev_hash != prev or ev.hash != _digest(prev, ev.ts, ev.actor, ev.action, ev.object):
            return False, ev.id
        prev = ev.hash
    return True, None
