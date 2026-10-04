"""Converts ORM rows to API dictionaries (camelCase for the React client)."""

from sqlalchemy.orm import Session

from . import governance as gov
from .models import AiModel, Asset, AuditEvent, Campaign, Cde, DqRule, GlossaryTerm, Issue, Policy, ReviewItem, Scan, Task


def cde(db: Session, c: Cde) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "domain": c.domain,
        "owner": c.owner,
        "formerOwner": c.former_owner,
        "steward": c.steward,
        "lineagePct": c.lineage_pct,
        "classification": c.classification,
        "attested": c.attested,
        "quality": gov.cde_quality(db, c.id),
        "status": gov.cde_status(db, c.id),
    }


def rule(r: DqRule) -> dict:
    return {
        "id": r.id,
        "name": r.name,
        "cdeId": r.cde_id,
        "dimension": r.dimension,
        "threshold": r.threshold,
        "lastValue": r.last_value,
        "status": gov.rule_status(r),
    }


def issue(i: Issue) -> dict:
    return {
        "id": i.id,
        "ruleId": i.rule_id,
        "cdeId": i.cde_id,
        "severity": i.severity,
        "owner": i.owner,
        "opened": i.opened,
        "due": i.due,
        "status": i.status,
        "note": i.note,
    }


def asset(db: Session, a: Asset) -> dict:
    return {
        "id": a.id,
        "name": a.name,
        "platform": a.platform,
        "domain": a.domain,
        "owner": a.owner,
        "formerOwner": a.former_owner,
        "steward": a.steward,
        "classification": a.classification,
        "certified": a.certified,
        "term": a.term,
        "cdeIds": a.cde_ids,
        "usage": a.usage,
        "qualityOk": all(gov.cde_status(db, c) != "breach" for c in a.cde_ids),
        "manualLineage": "EUC" in a.platform,
    }


def term(g: GlossaryTerm) -> dict:
    return {
        "id": g.id,
        "term": g.term,
        "definition": g.definition,
        "owner": g.owner,
        "status": g.status,
        "version": g.version,
        "proposedChange": g.proposed_change,
    }


def scan(s: Scan) -> dict:
    return {
        "id": s.id,
        "column": s.column_name,
        "dataset": s.dataset,
        "label": s.label,
        "confidence": s.confidence,
        "status": s.status,
    }


def policy(p: Policy) -> dict:
    return {"id": p.id, "name": p.name, "rule": p.rule, "scope": p.scope, "mode": p.mode}


def campaign(c: Campaign, decided_here: int) -> dict:
    done = c.others_done + decided_here
    return {
        "id": c.id,
        "name": c.name,
        "type": c.type,
        "due": c.due,
        "total": c.total,
        "done": done,
        "sealed": c.sealed,
        "evidenceId": c.evidence_id,
        "canSeal": (done >= c.total) and not c.sealed,
    }


def item(i: ReviewItem) -> dict:
    return {
        "id": i.id,
        "campaignId": i.campaign_id,
        "reviewer": i.reviewer,
        "kind": i.kind,
        "title": i.title,
        "tag": i.tag,
        "context": i.context,
        "recommendation": i.recommendation,
        "keepLabel": i.keep_label,
        "dropLabel": i.drop_label,
        "decision": i.decision,
    }


def task(t: Task) -> dict:
    return {"id": t.id, "title": t.title, "assignee": t.assignee, "due": t.due, "status": t.status, "source": t.source}


def model(db: Session, m: AiModel) -> dict:
    return {
        "id": m.id,
        "name": m.name,
        "version": m.version,
        "use": m.use,
        "type": m.model_type,
        "source": m.source,
        "tier": m.tier,
        "stage": m.stage,
        "owner": m.owner,
        "validator": m.validator,
        "validated": m.validated,
        "nextValidation": m.next_validation,
        "regulations": m.regulations,
        "dataCdes": [{"id": c, "status": gov.cde_status(db, c)} for c in m.data_cdes],
        "fairness": m.fairness,
        "performance": m.performance,
        "psi": m.psi,
        "llmEvals": m.llm_evals,
        "explainability": m.explainability,
        "approvals": m.approvals,
        "controls": m.controls,
        "alerts": gov.model_alerts(db, m),
    }


def audit_event(e: AuditEvent) -> dict:
    return {"id": e.id, "ts": e.ts, "actor": e.actor, "action": e.action, "object": e.object, "hash": e.hash}
