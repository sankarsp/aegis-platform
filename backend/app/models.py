"""Relational schema. Nested, rarely-queried attributes are JSON columns to keep the MVP schema small."""

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class Cde(Base):
    __tablename__ = "cdes"
    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    domain: Mapped[str] = mapped_column(String(80))
    owner: Mapped[str | None] = mapped_column(String(120), nullable=True)
    former_owner: Mapped[str | None] = mapped_column(String(120), nullable=True)
    steward: Mapped[str] = mapped_column(String(120))
    lineage_pct: Mapped[int] = mapped_column(Integer)
    classification: Mapped[str] = mapped_column(String(40))
    attested: Mapped[str] = mapped_column(String(10))


class DqRule(Base):
    __tablename__ = "dq_rules"
    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    cde_id: Mapped[str] = mapped_column(ForeignKey("cdes.id"))
    dimension: Mapped[str] = mapped_column(String(40))
    threshold: Mapped[float] = mapped_column(Float)
    last_value: Mapped[float] = mapped_column(Float)


class Issue(Base):
    __tablename__ = "issues"
    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    rule_id: Mapped[str] = mapped_column(String(20))
    cde_id: Mapped[str] = mapped_column(String(120))
    severity: Mapped[str] = mapped_column(String(20))
    owner: Mapped[str] = mapped_column(String(120))
    opened: Mapped[str] = mapped_column(String(10))
    due: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(30))
    note: Mapped[str] = mapped_column(Text)


class Report(Base):
    __tablename__ = "reports"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    regulation: Mapped[str] = mapped_column(String(200))
    cadence: Mapped[str] = mapped_column(String(60))
    owner: Mapped[str] = mapped_column(String(120))
    cde_ids: Mapped[list] = mapped_column(JSON)
    principles: Mapped[dict] = mapped_column(JSON)


class LineageNode(Base):
    __tablename__ = "lineage_nodes"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    report_id: Mapped[str] = mapped_column(ForeignKey("reports.id"))
    label: Mapped[str] = mapped_column(String(120))
    sub: Mapped[str] = mapped_column(String(120))
    col: Mapped[float] = mapped_column(Float)
    row: Mapped[float] = mapped_column(Float)
    is_report: Mapped[bool] = mapped_column(Boolean, default=False)
    is_euc: Mapped[bool] = mapped_column(Boolean, default=False)
    owner: Mapped[str] = mapped_column(String(120))
    cde_ids: Mapped[list] = mapped_column(JSON)
    controls: Mapped[list] = mapped_column(JSON)


class LineageEdge(Base):
    __tablename__ = "lineage_edges"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_id: Mapped[str] = mapped_column(ForeignKey("reports.id"))
    source: Mapped[str] = mapped_column(String(40))
    target: Mapped[str] = mapped_column(String(40))
    kind: Mapped[str] = mapped_column(String(10), default="auto")  # auto | manual | signed
    signed_by: Mapped[str | None] = mapped_column(String(120), nullable=True)


class Asset(Base):
    __tablename__ = "assets"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    platform: Mapped[str] = mapped_column(String(80))
    domain: Mapped[str] = mapped_column(String(80))
    owner: Mapped[str | None] = mapped_column(String(120), nullable=True)
    former_owner: Mapped[str | None] = mapped_column(String(120), nullable=True)
    steward: Mapped[str] = mapped_column(String(120))
    classification: Mapped[str] = mapped_column(String(40))
    certified: Mapped[bool] = mapped_column(Boolean, default=False)
    term: Mapped[str] = mapped_column(String(120))
    cde_ids: Mapped[list] = mapped_column(JSON)
    usage: Mapped[str] = mapped_column(String(80))


class GlossaryTerm(Base):
    __tablename__ = "glossary_terms"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    term: Mapped[str] = mapped_column(String(120), unique=True)
    definition: Mapped[str] = mapped_column(Text)
    owner: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(30))
    version: Mapped[str] = mapped_column(String(20))
    proposed_change: Mapped[str | None] = mapped_column(Text, nullable=True)
    proposed_definition: Mapped[str | None] = mapped_column(Text, nullable=True)


class Scan(Base):
    __tablename__ = "classification_scans"
    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    column_name: Mapped[str] = mapped_column(String(200))
    dataset: Mapped[str] = mapped_column(String(200))
    label: Mapped[str] = mapped_column(String(120))
    confidence: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20))  # Proposed | Confirmed | Rejected


class Policy(Base):
    __tablename__ = "access_policies"
    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    rule: Mapped[str] = mapped_column(Text)
    scope: Mapped[str] = mapped_column(String(200))
    mode: Mapped[str] = mapped_column(String(20))  # Enforced | Monitor only


class Campaign(Base):
    __tablename__ = "campaigns"
    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    type: Mapped[str] = mapped_column(String(40))
    due: Mapped[str] = mapped_column(String(10))
    total: Mapped[int] = mapped_column(Integer)
    others_done: Mapped[int] = mapped_column(Integer)  # completed by reviewers outside this demo tenant
    sealed: Mapped[bool] = mapped_column(Boolean, default=False)
    evidence_id: Mapped[str | None] = mapped_column(String(40), nullable=True)


class ReviewItem(Base):
    __tablename__ = "review_items"
    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    campaign_id: Mapped[str] = mapped_column(ForeignKey("campaigns.id"))
    reviewer: Mapped[str] = mapped_column(String(120))
    kind: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(300))
    tag: Mapped[str] = mapped_column(String(20))
    context: Mapped[list] = mapped_column(JSON)
    recommendation: Mapped[str] = mapped_column(Text)
    keep_label: Mapped[str] = mapped_column(String(60))
    drop_label: Mapped[str] = mapped_column(String(60))
    decision: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(300))
    assignee: Mapped[str] = mapped_column(String(120))
    due: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(20), default="Open")
    source: Mapped[str] = mapped_column(String(60))


class AiModel(Base):
    __tablename__ = "ai_models"
    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    version: Mapped[str] = mapped_column(String(20))
    use: Mapped[str] = mapped_column(Text)
    model_type: Mapped[str] = mapped_column(String(80))
    source: Mapped[str] = mapped_column(String(80))
    tier: Mapped[str] = mapped_column(String(10))
    stage: Mapped[str] = mapped_column(String(60))
    prev_stage: Mapped[str | None] = mapped_column(String(60), nullable=True)
    owner: Mapped[str] = mapped_column(String(120))
    validator: Mapped[str] = mapped_column(String(120))
    validated: Mapped[str] = mapped_column(String(20))
    next_validation: Mapped[str] = mapped_column(String(40))
    regulations: Mapped[list] = mapped_column(JSON)
    data_cdes: Mapped[list] = mapped_column(JSON)
    fairness: Mapped[list | None] = mapped_column(JSON, nullable=True)
    performance: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    psi: Mapped[float | None] = mapped_column(Float, nullable=True)
    llm_evals: Mapped[list | None] = mapped_column(JSON, nullable=True)
    explainability: Mapped[str] = mapped_column(Text)
    approvals: Mapped[list] = mapped_column(JSON)
    controls: Mapped[list] = mapped_column(JSON)


class AuditEvent(Base):
    """Append-only. Each row carries the hash of the previous row, so any edit breaks the chain."""

    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[str] = mapped_column(String(32))
    actor: Mapped[str] = mapped_column(String(120))
    action: Mapped[str] = mapped_column(Text)
    object: Mapped[str] = mapped_column(String(300))
    prev_hash: Mapped[str] = mapped_column(String(64))
    hash: Mapped[str] = mapped_column(String(64))


class PaymentRail(Base):
    """A payment type the fintech offers (ACH, wires, real-time rails, cross-border), with its rules and metrics."""

    __tablename__ = "payment_rails"
    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    category: Mapped[str] = mapped_column(String(40))  # Batch | Real-time | High-value RTGS | Cross-border | Product
    operator: Mapped[str] = mapped_column(String(160))
    region: Mapped[str] = mapped_column(String(40))
    description: Mapped[str] = mapped_column(Text)
    message_standard: Mapped[str] = mapped_column(String(200))
    settlement: Mapped[str] = mapped_column(String(200))
    availability: Mapped[str] = mapped_column(String(120))
    txn_limit: Mapped[str] = mapped_column(String(160))
    routes_to: Mapped[list] = mapped_column(JSON)
    regulations: Mapped[list] = mapped_column(JSON)  # [{name, note}]
    changes: Mapped[list] = mapped_column(JSON)  # [{date, text}] rule and standard changes, past and upcoming
    cde_ids: Mapped[list] = mapped_column(JSON)
    model_ids: Mapped[list] = mapped_column(JSON)
    report_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    metrics: Mapped[dict] = mapped_column(JSON)
    controls: Mapped[list] = mapped_column(JSON)
