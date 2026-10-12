"""Payment rails demo data for Northwind Pay (fictional): ACH, wires, Fedwire, Swift, RTP, FedNow and SEPA Instant.

Loaded on start-up whenever the payment_rails table is empty, so existing demo databases pick it up too.
Rule-change dates are real (checked October 2026; month only where the exact day was not confirmed); volumes and quality figures are examples.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import audit
from .models import (
    AiModel,
    Asset,
    Cde,
    DqRule,
    GlossaryTerm,
    Issue,
    LineageEdge,
    LineageNode,
    PaymentRail,
    Report,
)

# id, name, domain, owner, steward, lineage %, classification
PAYMENT_CDES = [
    ("pay.originator_name", "Originator name", "Payments", "Priya Nair", "Marco Diaz", 100, "PII"),
    ("pay.originator_address", "Originator address", "Payments", "Priya Nair", "Marco Diaz", 92, "PII"),
    ("pay.beneficiary_name", "Beneficiary name", "Payments", "Priya Nair", "Marco Diaz", 100, "PII"),
    (
        "pay.beneficiary_account",
        "Beneficiary account (ABA, account no. or IBAN)",
        "Payments",
        "Priya Nair",
        "Marco Diaz",
        100,
        "Confidential",
    ),
    ("pay.uetr", "Unique end-to-end transaction reference (UETR)", "Payments", "Priya Nair", "Marco Diaz", 100, "Internal"),
    ("pay.end_to_end_id", "End-to-end identification", "Payments", "Priya Nair", "Marco Diaz", 100, "Internal"),
    ("pay.purpose_code", "Payment purpose code", "Payments", "Priya Nair", "Marco Diaz", 95, "Internal"),
    ("pay.vop_result", "Verification of Payee result", "Payments", "Priya Nair", "Sara Lim", 100, "Internal"),
    (
        "pay.sanctions_screening_result",
        "Sanctions screening result",
        "Compliance",
        "Aisha Rahman",
        "Tom Becker",
        100,
        "Confidential",
    ),
    ("ach.sec_code", "ACH Standard Entry Class code", "Payments", "Priya Nair", "Marco Diaz", 100, "Internal"),
    ("ach.trace_number", "ACH trace number", "Payments", "Priya Nair", "Marco Diaz", 100, "Internal"),
    ("ach.return_reason_code", "ACH return reason code", "Payments", "Priya Nair", "Marco Diaz", 100, "Internal"),
    ("ach.company_entry_description", "ACH company entry description", "Payments", "Priya Nair", "Marco Diaz", 100, "Internal"),
]

# id, name, cde, dimension, threshold %, last result %
PAYMENT_RULES = [
    ("DQ-201", "SEC code valid for the account type (CCD, PPD, WEB, IAT)", "ach.sec_code", "Validity", 99.9, 99.95),
    ("DQ-202", "Trace number unique within the settlement date", "ach.trace_number", "Uniqueness", 100, 100),
    (
        "DQ-203",
        "Entry description uses PAYROLL or PURCHASE where Nacha requires",
        "ach.company_entry_description",
        "Validity",
        99,
        93.4,
    ),
    ("DQ-204", "Return reason code is a valid Nacha R-code", "ach.return_reason_code", "Validity", 100, 100),
    ("DQ-205", "Originator name present on funds transfers of $3,000 or more", "pay.originator_name", "Completeness", 100, 99.2),
    ("DQ-206", "Originator address sent as structured ISO 20022 postal address", "pay.originator_address", "Validity", 95, 88.7),
    ("DQ-207", "UETR present on every Fedwire and Swift payment", "pay.uetr", "Completeness", 100, 100),
    ("DQ-208", "End-to-end ID unique per real-time payment", "pay.end_to_end_id", "Uniqueness", 100, 100),
    ("DQ-209", "Purpose code present where the corridor requires it", "pay.purpose_code", "Completeness", 98, 98.6),
    ("DQ-210", "Verification of Payee recorded before authorisation", "pay.vop_result", "Completeness", 100, 99.6),
    ("DQ-211", "Sanctions screening completed before release", "pay.sanctions_screening_result", "Timeliness", 100, 100),
    (
        "DQ-212",
        "Beneficiary account passes format and check-digit validation",
        "pay.beneficiary_account",
        "Validity",
        99.9,
        99.94,
    ),
]

PAYMENT_ISSUES = [
    (
        "ISS-2050",
        "DQ-203",
        "ach.company_entry_description",
        "High",
        "Marco Diaz",
        "2026-10-02",
        "2026-10-16",
        "Remediating",
        "Payroll partner files still send 'SALARY' and 'WAGES'; Nacha standard descriptions apply from 20 March 2026.",
    ),
    (
        "ISS-2051",
        "DQ-206",
        "pay.originator_address",
        "High",
        "Marco Diaz",
        "2026-10-05",
        "2026-10-30",
        "Investigating",
        "11% of outbound wires carry unstructured address lines from the legacy onboarding form.",
    ),
]

TRAVEL_REPORT = {
    "id": "travel",
    "name": "Funds transfer recordkeeping (Travel Rule)",
    "regulation": "BSA 31 CFR 1010.410(f); FATF Recommendation 16",
    "cadence": "Continuous; records kept 5 years",
    "owner": "Aisha Rahman",
    "cde_ids": [
        "pay.originator_name",
        "pay.originator_address",
        "pay.beneficiary_name",
        "pay.beneficiary_account",
        "pay.uetr",
        "pay.sanctions_screening_result",
        "txn.amount",
    ],
    "principles": {
        "Governance and infrastructure": 86,
        "Risk data aggregation": 83,
        "Risk reporting": 88,
        "Supervisory review": 82,
    },
    "nodes": [
        (
            "travel-1",
            "Fedwire gateway",
            "ISO 20022 pacs.008/009",
            0,
            0,
            False,
            False,
            "Priya Nair",
            ["pay.uetr", "pay.originator_address"],
            ["Message schema validation"],
        ),
        (
            "travel-2",
            "Swift gateway",
            "CBPR+ pacs.008/009",
            0,
            1,
            False,
            False,
            "Priya Nair",
            ["pay.uetr", "pay.purpose_code"],
            ["Message schema validation"],
        ),
        (
            "travel-3",
            "FedNow and RTP",
            "ISO 20022 pacs.008",
            0,
            2,
            False,
            False,
            "Priya Nair",
            ["pay.end_to_end_id"],
            ["End-to-end ID uniqueness"],
        ),
        (
            "travel-4",
            "Swift repairs",
            "repair_queue.xlsx",
            0,
            3,
            False,
            True,
            "Marco Diaz",
            ["pay.originator_address"],
            ["None registered"],
        ),
        ("travel-5", "payments.iso20022", "Kafka topic", 1, 1, False, False, "Platform team", [], ["Schema registry"]),
        (
            "travel-6",
            "Screening engine",
            "Sanctions decisions",
            1,
            2.5,
            False,
            False,
            "Aisha Rahman",
            ["pay.sanctions_screening_result"],
            ["DQ-211"],
        ),
        (
            "travel-7",
            "stg_payment_messages",
            "dbt model",
            2,
            1,
            False,
            False,
            "Marco Diaz",
            ["pay.originator_name", "pay.beneficiary_name", "pay.beneficiary_account"],
            ["DQ-205", "DQ-212"],
        ),
        (
            "travel-8",
            "int_funds_transfers",
            "dbt model",
            3,
            1.5,
            False,
            False,
            "Marco Diaz",
            ["pay.originator_address", "txn.amount"],
            ["DQ-206", "DQ-207"],
        ),
        (
            "travel-9",
            "mart_travel_rule",
            "Snowflake",
            4,
            1.5,
            False,
            False,
            "Aisha Rahman",
            ["pay.originator_name"],
            ["Retention: 5 years"],
        ),
        (
            "travel-10",
            "Travel Rule records",
            "Report · FinCEN, examiners",
            5,
            1.5,
            True,
            False,
            "Aisha Rahman",
            [],
            ["Quality gate"],
        ),
    ],
    "edges": [
        ("travel-1", "travel-5"),
        ("travel-2", "travel-5"),
        ("travel-3", "travel-5"),
        ("travel-5", "travel-7"),
        ("travel-7", "travel-8"),
        ("travel-6", "travel-8"),
        ("travel-4", "travel-8", "manual"),
        ("travel-8", "travel-9"),
        ("travel-9", "travel-10"),
    ],
}

PAYMENT_ASSETS = [
    (
        "payments.ach_entries",
        "Snowflake",
        "Payments",
        "Priya Nair",
        "Marco Diaz",
        "Internal",
        True,
        "ACH entry",
        ["ach.sec_code", "ach.trace_number", "ach.return_reason_code", "ach.company_entry_description"],
        "48 queries/day",
    ),
    (
        "payments.iso20022_messages",
        "Snowflake",
        "Payments",
        "Priya Nair",
        "Marco Diaz",
        "PII",
        True,
        "Funds transfer",
        ["pay.originator_name", "pay.originator_address", "pay.beneficiary_name", "pay.uetr", "pay.purpose_code"],
        "73 queries/day",
    ),
    (
        "payments.sepa_inst_transfers",
        "Snowflake (EU region)",
        "Payments",
        "Priya Nair",
        "Sara Lim",
        "PII",
        False,
        "SEPA instant credit transfer",
        ["pay.vop_result", "pay.beneficiary_account", "pay.end_to_end_id"],
        "17 queries/day",
    ),
    (
        "screening.sanctions_decisions",
        "Postgres",
        "Compliance",
        "Aisha Rahman",
        "Tom Becker",
        "Confidential",
        True,
        "Sanctions screening result",
        ["pay.sanctions_screening_result"],
        "Source system",
    ),
]

PAYMENT_TERMS = [
    (
        "UETR",
        "Unique end-to-end transaction reference: a UUID that stays with a Swift or Fedwire payment from first instruction to final credit, used to trace it across banks.",
        "Priya Nair",
    ),
    (
        "Standard Entry Class (SEC) code",
        "Three-letter Nacha code on every ACH batch that says what kind of entry it is, such as CCD for business payments, PPD for consumer prearranged payments and WEB for internet-initiated debits.",
        "Priya Nair",
    ),
    (
        "Verification of Payee",
        "Check, before a euro credit transfer is authorised, that the payee name matches the IBAN. Returns match, close match, no match or not possible. Required under the EU Instant Payments Regulation.",
        "Priya Nair",
    ),
    (
        "Travel Rule",
        "Requirement that originator and beneficiary information travels with funds transfers of $3,000 or more and is kept as a record (31 CFR 1010.410(f)); FATF Recommendation 16 sets the global standard.",
        "Aisha Rahman",
    ),
]

FRAUD_MODEL = dict(
    id="M7",
    name="Payment fraud monitoring",
    version="v1.4",
    use="Scores outgoing ACH, RTP, FedNow and SEPA Instant payments for account takeover and authorised push payment fraud",
    model_type="Gradient-boosted trees with rules",
    source="In-house",
    tier="High",
    stage="Production",
    owner="Kenji Watanabe",
    validator="Model Risk Management",
    validated="2026-03-02",
    next_validation="2027-03-02",
    regulations=[
        "Nacha risk-based fraud monitoring (2026 rules)",
        "Reg E: unauthorized transfers",
        "SR 11-7: model risk management",
        "UDAAP",
    ],
    data_cdes=["txn.amount", "pay.beneficiary_account", "pay.beneficiary_name", "pay.vop_result"],
    fairness=None,
    performance={"metric": "Fraud caught at 1% review rate", "value": 0.64, "baseline": 0.66},
    psi=0.14,
    llm_evals=None,
    explainability="Top risk factors shown to the fraud analyst and stored with each hold decision",
    approvals=[
        {"step": "Model owner", "approved": True},
        {"step": "Independent validation", "approved": True},
        {"step": "AI risk committee", "approved": True},
    ],
    controls=[
        "Holds above score 0.9 for real-time rails",
        "Beneficiary allow lists",
        "Weekly drift report",
        "Rules-based fallback",
    ],
)

RAILS = [
    dict(
        id="ach",
        name="ACH",
        category="Batch",
        region="United States",
        operator="Nacha Operating Rules; Federal Reserve FedACH and The Clearing House EPN",
        description="Payroll, bill payments and account funding in batches. Northwind Pay originates through its sponsor bank (ODFI).",
        message_standard="Nacha fixed-width files (94-character records)",
        settlement="Same Day ACH windows or next day, net settlement",
        availability="Business days",
        txn_limit="$1 million per Same Day ACH payment; no limit for next-day ACH",
        routes_to=[],
        regulations=[
            {"name": "Nacha Operating Rules", "note": "Return rate thresholds, SEC code use, risk-based fraud monitoring"},
            {"name": "Regulation E", "note": "Consumer error resolution and unauthorized debits"},
            {"name": "OFAC sanctions", "note": "Screening of IAT entries and originators"},
            {"name": "Bank Secrecy Act", "note": "Monitoring and SAR filing for suspicious ACH activity"},
        ],
        changes=[
            {
                "date": "2026-03-20",
                "text": "Nacha fraud monitoring phase 1 (originators with 6 million+ ACH entries in 2023) and standard PAYROLL / PURCHASE descriptions",
            },
            {"date": "2026-06-22", "text": "Nacha fraud monitoring phase 2 for all other originators and receiving banks"},
            {"date": "2026-09-18", "text": "New IAT definition and 9:00 a.m. availability for non-same-day ACH credits"},
        ],
        cde_ids=[
            "ach.sec_code",
            "ach.trace_number",
            "ach.company_entry_description",
            "ach.return_reason_code",
            "txn.amount",
            "pay.sanctions_screening_result",
        ],
        model_ids=["M7", "M3"],
        report_id=None,
        metrics={
            "volume30d": 412880,
            "value30dUsd": 1_940_000_000,
            "screeningPct": 100.0,
            "travelRulePct": None,
            "returnRate": {"label": "Unauthorized return rate", "value": 0.31, "threshold": 0.5, "unit": "%"},
        },
        controls=[
            "ODFI exposure limits per originator",
            "Prenote for new payroll accounts",
            "Unauthorized return monitoring against the 0.5% Nacha threshold",
        ],
    ),
    dict(
        id="wire",
        name="Wire transfers",
        category="Product",
        region="United States and cross-border",
        operator="Northwind Pay wire desk through its sponsor bank",
        description="Customer wire product. Domestic wires go out over Fedwire and cross-border wires over Swift, so one wire record feeds both rails.",
        message_standard="ISO 20022 pacs.008 (customer) and pacs.009 (bank)",
        settlement="Settles on the rail it is routed to",
        availability="Business days, cut-off 5:00 p.m. ET",
        txn_limit="Customer limits by risk tier",
        routes_to=["fedwire", "swift"],
        regulations=[
            {"name": "UCC Article 4A", "note": "Rights and liabilities for funds transfers, including security procedures"},
            {
                "name": "BSA Travel Rule (31 CFR 1010.410(f))",
                "note": "Originator and beneficiary data on transfers of $3,000 or more, kept 5 years",
            },
            {"name": "OFAC sanctions", "note": "Screen originator, beneficiary and banks before release"},
            {"name": "FATF Recommendation 16", "note": "Revised June 2025: more complete originator and beneficiary data"},
        ],
        changes=[{"date": "2025-06", "text": "FATF adopts revised Recommendation 16 on payment transparency"}],
        cde_ids=[
            "pay.originator_name",
            "pay.originator_address",
            "pay.beneficiary_name",
            "pay.beneficiary_account",
            "pay.sanctions_screening_result",
            "txn.amount",
        ],
        model_ids=["M3"],
        report_id="travel",
        metrics={
            "volume30d": 18440,
            "value30dUsd": 2_310_000_000,
            "screeningPct": 100.0,
            "travelRulePct": 99.2,
            "returnRate": {"label": "Wires recalled or returned", "value": 0.4, "threshold": 1.0, "unit": "%"},
        },
        controls=[
            "Call-back verification above $50,000",
            "Dual approval for new beneficiaries",
            "Sanctions hold queue with 4-eyes release",
        ],
    ),
    dict(
        id="fedwire",
        name="Fedwire Funds",
        category="High-value RTGS",
        region="United States",
        operator="Federal Reserve Banks",
        description="Domestic high-value wires settled one by one in central bank money.",
        message_standard="ISO 20022 since 14 July 2025 (pacs.008, pacs.009, pacs.004)",
        settlement="Real-time gross settlement, final and irrevocable",
        availability="Business days, extended hours",
        txn_limit="No network limit",
        routes_to=[],
        regulations=[
            {"name": "Regulation J and Operating Circular 6", "note": "Fedwire Funds Service terms"},
            {"name": "UCC Article 4A", "note": "Funds transfer law"},
            {"name": "BSA Travel Rule", "note": "Originator and beneficiary data for $3,000 or more"},
            {"name": "OFAC sanctions", "note": "Screen before release"},
        ],
        changes=[{"date": "2025-07-14", "text": "Fedwire Funds Service moved from FAIM to ISO 20022 messages"}],
        cde_ids=[
            "pay.uetr",
            "pay.originator_name",
            "pay.originator_address",
            "pay.beneficiary_account",
            "pay.sanctions_screening_result",
        ],
        model_ids=["M3"],
        report_id="travel",
        metrics={
            "volume30d": 12960,
            "value30dUsd": 1_720_000_000,
            "screeningPct": 100.0,
            "travelRulePct": 99.4,
            "returnRate": {"label": "Rejected by Fedwire", "value": 0.2, "threshold": 0.5, "unit": "%"},
        },
        controls=["ISO 20022 schema validation before send", "Structured address check (DQ-206)"],
    ),
    dict(
        id="swift",
        name="Swift cross-border",
        category="Cross-border",
        region="Global",
        operator="Swift network through correspondent banks",
        description="Cross-border wires and FX payments through the sponsor bank's correspondents.",
        message_standard="ISO 20022 CBPR+; MT103 and MT202 retired after 22 Nov 2025",
        settlement="Through correspondent (nostro) accounts",
        availability="Business days in each currency",
        txn_limit="No network limit",
        routes_to=[],
        regulations=[
            {"name": "FATF Recommendation 16", "note": "Payment transparency across borders"},
            {"name": "BSA Travel Rule", "note": "Originator and beneficiary data for $3,000 or more"},
            {"name": "OFAC, EU and UK sanctions", "note": "Screen parties, banks and countries"},
            {"name": "EU Transfer of Funds Regulation", "note": "Applies to payments touching EU banks"},
        ],
        changes=[
            {"date": "2025-11-22", "text": "End of MT and ISO 20022 coexistence for cross-border payment instructions"},
            {
                "date": "2026-12",
                "text": "Swift to confirm the new date for retiring unstructured postal addresses in CBPR+ (was 14 Nov 2026; deferred on 27 Aug 2026)",
            },
        ],
        cde_ids=[
            "pay.uetr",
            "pay.purpose_code",
            "pay.originator_name",
            "pay.originator_address",
            "pay.beneficiary_name",
            "pay.sanctions_screening_result",
        ],
        model_ids=["M3"],
        report_id="travel",
        metrics={
            "volume30d": 5480,
            "value30dUsd": 590_000_000,
            "screeningPct": 100.0,
            "travelRulePct": 98.7,
            "returnRate": {"label": "Payments needing manual repair", "value": 3.8, "threshold": 2.0, "unit": "%"},
        },
        controls=["Tracked end to end with UETR", "Repair queue reviewed daily", "High-risk corridor review"],
    ),
    dict(
        id="rtp",
        name="RTP",
        category="Real-time",
        region="United States",
        operator="The Clearing House",
        description="Instant credit transfers for payouts and account funding, available around the clock.",
        message_standard="ISO 20022 (pacs.008, request for payment pain.013)",
        settlement="Real time, from a prefunded joint account at the Federal Reserve",
        availability="24x7x365",
        txn_limit="$10 million per payment (raised February 2025)",
        routes_to=[],
        regulations=[
            {"name": "RTP Operating Rules", "note": "Participant obligations, irrevocability"},
            {"name": "Regulation E", "note": "Consumer error resolution"},
            {"name": "OFAC sanctions", "note": "Real-time screening before release"},
            {"name": "Bank Secrecy Act", "note": "Monitoring for suspicious activity"},
        ],
        changes=[{"date": "2025-02", "text": "RTP network limit raised from $1 million to $10 million"}],
        cde_ids=[
            "pay.end_to_end_id",
            "pay.beneficiary_name",
            "pay.beneficiary_account",
            "pay.sanctions_screening_result",
            "txn.amount",
        ],
        model_ids=["M7", "M3"],
        report_id="travel",
        metrics={
            "volume30d": 96320,
            "value30dUsd": 410_000_000,
            "screeningPct": 100.0,
            "travelRulePct": 99.6,
            "returnRate": {"label": "Payments rejected", "value": 0.6, "threshold": 1.0, "unit": "%"},
        },
        controls=["Real-time fraud score before send (M7)", "Per-customer velocity limits", "New payee cooling-off period"],
    ),
    dict(
        id="fednow",
        name="FedNow",
        category="Real-time",
        region="United States",
        operator="Federal Reserve Banks",
        description="Instant payments around the clock through the Federal Reserve, used for payouts and pay-by-bank.",
        message_standard="ISO 20022 (pacs.008, pacs.002)",
        settlement="Real time in Federal Reserve master accounts",
        availability="24x7x365",
        txn_limit="$10 million network limit (raised November 2025); firms set lower limits",
        routes_to=[],
        regulations=[
            {"name": "Regulation J subpart C and Operating Circular 8", "note": "FedNow Service terms"},
            {"name": "Regulation E", "note": "Consumer error resolution"},
            {"name": "OFAC sanctions", "note": "Screening before release"},
            {"name": "Bank Secrecy Act", "note": "Monitoring for suspicious activity"},
        ],
        changes=[{"date": "2025-11", "text": "FedNow network limit raised from $1 million to $10 million"}],
        cde_ids=[
            "pay.end_to_end_id",
            "pay.beneficiary_name",
            "pay.beneficiary_account",
            "pay.sanctions_screening_result",
            "txn.amount",
        ],
        model_ids=["M7"],
        report_id="travel",
        metrics={
            "volume30d": 41250,
            "value30dUsd": 168_000_000,
            "screeningPct": 100.0,
            "travelRulePct": 99.5,
            "returnRate": {"label": "Payments rejected", "value": 0.5, "threshold": 1.0, "unit": "%"},
        },
        controls=[
            "Real-time fraud score before send (M7)",
            "Institution-set transaction limit of $500,000",
            "Negative payee list",
        ],
    ),
    dict(
        id="sepa_inst",
        name="Instant Payment (SEPA Inst)",
        category="Real-time",
        region="Euro area",
        operator="EPC SCT Inst scheme; settled through TIPS and EBA RT1",
        description="Euro instant credit transfers from Northwind Pay's EU entity, settled in seconds.",
        message_standard="ISO 20022 (pacs.008), EPC SCT Inst rulebook",
        settlement="Within 10 seconds, around the clock",
        availability="24x7x365",
        txn_limit="No scheme maximum; customers must be able to set their own limits",
        routes_to=[],
        regulations=[
            {
                "name": "EU Instant Payments Regulation (2024/886)",
                "note": "Send instant payments, price parity, Verification of Payee",
            },
            {"name": "Sanctions screening under the IPR", "note": "Screen own customers at least daily instead of each payment"},
            {"name": "EU Transfer of Funds Regulation", "note": "Payer and payee information on transfers"},
            {"name": "PSD2", "note": "Strong customer authentication and fraud reporting"},
        ],
        changes=[
            {"date": "2025-10-09", "text": "Euro-area PSPs must send instant payments and offer Verification of Payee"},
            {
                "date": "2027-07-09",
                "text": "PSPs in non-euro EU countries must send euro instant payments and offer Verification of Payee",
            },
        ],
        cde_ids=[
            "pay.vop_result",
            "pay.beneficiary_name",
            "pay.beneficiary_account",
            "pay.end_to_end_id",
            "pay.sanctions_screening_result",
        ],
        model_ids=["M7"],
        report_id=None,
        metrics={
            "volume30d": 27610,
            "value30dUsd": 52_000_000,
            "screeningPct": 100.0,
            "travelRulePct": None,
            "returnRate": {"label": "Verification of Payee: no match", "value": 1.7, "threshold": 3.0, "unit": "%"},
        },
        controls=[
            "Daily customer screening against EU lists",
            "Verification of Payee before authorisation",
            "Customer-set payment limits",
        ],
    ),
]


REFERENCE_FIELDS = (
    "name",
    "category",
    "operator",
    "region",
    "description",
    "message_standard",
    "settlement",
    "availability",
    "txn_limit",
    "routes_to",
    "regulations",
    "changes",
    "controls",
)


def sync_rail_reference(db: Session) -> int:
    """Keeps rail reference data (rules, limits, dated changes) current on databases seeded by an older release.
    Metrics and links stay as they are. Returns how many rails changed."""
    changed = 0
    for spec in RAILS:
        r = db.get(PaymentRail, spec["id"])
        if not r:
            continue
        diff = [f for f in REFERENCE_FIELDS if getattr(r, f) != spec[f]]
        for f in diff:
            setattr(r, f, spec[f])
        changed += bool(diff)
    if changed:
        db.commit()
    return changed


def seed_payments(db: Session) -> bool:
    """Adds the payment-rails demo data if it is not there yet, or refreshes its reference data. Safe on every start.
    Returns True when anything was added or changed, so the caller re-indexes search."""
    if db.scalar(select(PaymentRail).limit(1)):
        return sync_rail_reference(db) > 0
    for c in PAYMENT_CDES:
        if not db.get(Cde, c[0]):
            db.add(
                Cde(
                    id=c[0],
                    name=c[1],
                    domain=c[2],
                    owner=c[3],
                    steward=c[4],
                    lineage_pct=c[5],
                    classification=c[6],
                    attested="2026-06-30",
                )
            )
    db.flush()
    for r in PAYMENT_RULES:
        if not db.get(DqRule, r[0]):
            db.add(DqRule(id=r[0], name=r[1], cde_id=r[2], dimension=r[3], threshold=r[4], last_value=r[5]))
    for i in PAYMENT_ISSUES:
        if not db.get(Issue, i[0]):
            db.add(
                Issue(
                    id=i[0], rule_id=i[1], cde_id=i[2], severity=i[3], owner=i[4], opened=i[5], due=i[6], status=i[7], note=i[8]
                )
            )
    rp = TRAVEL_REPORT
    if not db.get(Report, rp["id"]):
        db.add(
            Report(
                id=rp["id"],
                name=rp["name"],
                regulation=rp["regulation"],
                cadence=rp["cadence"],
                owner=rp["owner"],
                cde_ids=rp["cde_ids"],
                principles=rp["principles"],
            )
        )
        db.flush()
        db.add_all(
            LineageNode(
                id=n[0],
                report_id=rp["id"],
                label=n[1],
                sub=n[2],
                col=n[3],
                row=n[4],
                is_report=n[5],
                is_euc=n[6],
                owner=n[7],
                cde_ids=n[8],
                controls=n[9],
            )
            for n in rp["nodes"]
        )
        db.add_all(
            LineageEdge(report_id=rp["id"], source=e[0], target=e[1], kind=e[2] if len(e) > 2 else "auto") for e in rp["edges"]
        )
    existing = set(db.scalars(select(Asset.name)))
    db.add_all(
        Asset(
            name=a[0],
            platform=a[1],
            domain=a[2],
            owner=a[3],
            steward=a[4],
            classification=a[5],
            certified=a[6],
            term=a[7],
            cde_ids=a[8],
            usage=a[9],
        )
        for a in PAYMENT_ASSETS
        if a[0] not in existing
    )
    terms = set(db.scalars(select(GlossaryTerm.term)))
    db.add_all(
        GlossaryTerm(term=t[0], definition=t[1], owner=t[2], status="Approved", version="v1")
        for t in PAYMENT_TERMS
        if t[0] not in terms
    )
    if not db.get(AiModel, FRAUD_MODEL["id"]):
        db.add(AiModel(**FRAUD_MODEL))
    db.add_all(PaymentRail(**r) for r in RAILS)
    db.flush()
    audit.record(db, "Aegis setup", "Added payment rails: ACH, wires, Fedwire, Swift, RTP, FedNow, SEPA Instant", "Payment rails")
    db.commit()
    return True
