def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_overview_kpis_and_attention(client):
    body = client.get("/api/overview").json()
    k = body["kpis"]
    assert k["cdesTotal"] == 25 and k["cdesOwned"] == 24
    assert k["models"] == 7
    titles = [a["title"] for a in body["attention"]]
    assert any("customer.date_of_birth has no owner" in t for t in titles)
    assert any("Card fraud scoring" in t for t in titles)  # drift and overdue validation
    assert body["auditChainIntact"] is True


def test_lineage_signoff_raises_completeness(client):
    rp = client.get("/api/reports/recon").json()
    assert rp["completeness"] == 90
    manual = next(e for e in rp["edges"] if e["kind"] == "manual")
    r = client.post(f"/api/reports/recon/edges/{manual['id']}/signoff")
    assert r.status_code == 200 and r.json()["completeness"] == 100
    assert client.post(f"/api/reports/recon/edges/{manual['id']}/signoff").status_code == 409


def test_impact_analysis_follows_edges(client):
    body = client.get("/api/reports/recon/nodes/recon-1/impact").json()
    assert any("mart_daily_recon" in d for d in body["downstream"])
    assert "SAR and CTR filing feed" in body["otherReports"]


def test_sar_report_is_held_until_issue_resolved(client):
    gates = {g["reportId"]: g for g in client.get("/api/quality/gates").json()}
    assert gates["sar"]["held"] is True
    for iss in client.get("/api/quality/issues").json():
        if iss["status"] != "Closed" and iss["cdeId"] in gates["sar"]["breached_cdes"]:
            client.post(f"/api/quality/issues/{iss['id']}/resolve")
    gates = {g["reportId"]: g for g in client.get("/api/quality/gates").json()}
    assert gates["sar"]["held"] is False


def test_assign_owner_fixes_orphaned_cde(client):
    a = next(x for x in client.get("/api/catalog/assets?q=customer_profile").json())
    assert a["owner"] is None
    r = client.post(f"/api/catalog/assets/{a['id']}/owner", json={"owner": "Sara Lim"})
    assert r.json()["owner"] == "Sara Lim"
    cde = next(c for c in client.get("/api/catalog/cdes").json() if c["id"] == "customer.date_of_birth")
    assert cde["owner"] == "Sara Lim"


def test_semantic_search_finds_relevant_records(client):
    res = client.get("/api/search", params={"q": "credit limit decisions fairness"}).json()["results"]
    assert res[0]["kind"] == "model" and "Credit line" in res[0]["title"]
    res = client.get("/api/search", params={"q": "sponsor bank settlement"}).json()["results"]
    assert any(r["refId"] == "recon" for r in res[:3])


def test_classification_suggestion_uses_confirmed_labels(client):
    s = client.post("/api/access/suggest-classification", json={"column": "contact_email"}).json()
    assert s["suggestion"] == "PII · Email address"


def test_similar_glossary_terms(client):
    hits = client.get("/api/catalog/glossary/similar", params={"text": "settlement position owed to sponsor bank"}).json()
    assert hits[0]["term"] == "Net settlement position"


def test_recert_decision_creates_task_and_seal(client):
    items = client.get("/api/recert/inbox").json()
    for it in items:
        if it["campaignId"] == "C3":
            r = client.post(f"/api/recert/items/{it['id']}/decision", json={"keep": it["id"] != "R6", "note": "test"})
            assert r.status_code == 200
    tasks = client.get("/api/recert/tasks").json()
    assert any("Fix lineage gaps" in t["title"] for t in tasks)
    c3 = next(c for c in client.get("/api/recert/campaigns").json() if c["id"] == "C3")
    assert c3["canSeal"]
    sealed = client.post("/api/recert/campaigns/C3/seal").json()
    assert sealed["sealed"] and sealed["evidenceId"].startswith("EV-")


def test_reviewer_cannot_act_on_someone_elses_item(client):
    it = client.get("/api/recert/inbox").json()[0]
    r = client.post(f"/api/recert/items/{it['id']}/decision", json={"keep": True}, headers={"X-User": "Ravi Shah"})
    assert r.status_code == 403


def test_ai_mitigation_requires_reapproval_by_different_people(client):
    m = client.get("/api/ai/models/M1").json()
    assert any(a["level"] == "crit" for a in m["alerts"])
    m = client.post("/api/ai/models/M1/mitigate").json()
    assert all(f["value"] >= 0.8 for f in m["fairness"])
    assert m["stage"] == "Awaiting approval" and m["version"] == "v4.3"
    # The person who mitigated signed the owner step, so they cannot sign the next one.
    assert client.post("/api/ai/models/M1/approve").status_code == 403
    for approver in ["validator@example.com", "fairlending@example.com", "committee@example.com"]:
        r = client.post("/api/ai/models/M1/approve", headers={"X-User": approver})
        assert r.status_code == 200
    assert r.json()["stage"] == "Production"


def test_paused_model_cannot_be_changed(client):
    client.post("/api/ai/models/M5/pause")
    assert client.post("/api/ai/models/M5/mitigate").status_code == 409
    client.post("/api/ai/models/M5/pause")


def test_roles_are_enforced():
    import pytest
    from fastapi import HTTPException

    from app.auth import User, require

    viewer = User(id="v@example.com", name="Viewer", roles=frozenset())
    with pytest.raises(HTTPException) as e:
        require("admin")(viewer)
    assert e.value.status_code == 403
    assert require("steward")(User(id="s@example.com", name="S", roles=frozenset({"steward"}))).id == "s@example.com"


def test_ai_pause_and_resume(client):
    m = client.post("/api/ai/models/M2/pause").json()
    assert m["stage"].startswith("Paused")
    m = client.post("/api/ai/models/M2/pause").json()
    assert m["stage"] == "Production"


def test_evidence_pack_and_audit_chain(client):
    pack = client.post("/api/reports/pci/evidence-pack").json()
    assert pack["id"].startswith("EV-") and "PCI DSS" in pack["text"]
    log = client.get("/api/audit").json()
    assert log["intact"] and log["events"][0]["action"].startswith("Generated evidence pack")


def test_audit_chain_detects_tampering(client):
    from app.audit import verify_chain
    from app.db import SessionLocal
    from app.models import AuditEvent

    with SessionLocal() as db:
        ev = db.get(AuditEvent, 3)
        original = ev.action
        ev.action = "Quietly edited"
        db.flush()
        assert verify_chain(db) == (False, 3)
        ev.action = original
        db.commit()
        assert verify_chain(db)[0]


def test_cognito_mode_rejects_missing_or_bad_tokens(client, monkeypatch):
    from app.config import get_settings

    s = get_settings()
    monkeypatch.setattr(s, "cognito_user_pool_id", "us-east-1_example")
    monkeypatch.setattr(s, "cognito_client_id", "client123")
    assert client.get("/api/me").status_code == 401
    assert client.get("/api/overview").status_code == 401  # read routes are protected too
    assert client.get("/health").status_code == 200
    assert client.get("/api/me", headers={"Authorization": "Bearer not-a-jwt"}).status_code == 401


def test_database_url_built_from_parts():
    from app.config import Settings

    s = Settings(db_host="db.internal", db_user="aegis", db_password="p@ss/word")
    assert s.database_url == "postgresql+psycopg://aegis:p%40ss%2Fword@db.internal:5432/aegis?sslmode=require"


def test_all_payment_rails_are_listed_in_order(client):
    rails = client.get("/api/payments/rails").json()
    assert [r["id"] for r in rails] == ["ach", "wire", "fedwire", "swift", "rtp", "fednow", "sepa_inst"]
    wire = next(r for r in rails if r["id"] == "wire")
    assert wire["routesTo"] == ["fedwire", "swift"]


def test_ach_rail_shows_nacha_rule_breach_and_changes(client):
    ach = client.get("/api/payments/rails/ach").json()
    assert ach["quality"] == "breach"
    assert any(r["id"] == "DQ-203" and r["status"] == "breach" for r in ach["rules"])
    assert any("Nacha fraud monitoring phase 1" in c["text"] for c in ach["changes"])
    assert any(i["id"] == "ISS-2050" for i in ach["issues"])
    assert any(m["id"] == "M7" for m in ach["models"])


def test_swift_rail_flags_repair_rate_and_links_travel_rule_report(client):
    swift = client.get("/api/payments/rails/swift").json()
    assert swift["rateOver"] is True
    assert swift["report"]["id"] == "travel"
    travel = client.get("/api/reports/travel").json()
    assert travel["gate"]["held"] is True  # DQ-206 structured address breach
    assert any(e["kind"] == "manual" for e in travel["edges"])


def test_unknown_rail_is_404(client):
    assert client.get("/api/payments/rails/cheque").status_code == 404


def test_search_finds_rails(client):
    res = client.get("/api/search", params={"q": "Verification of Payee euro instant"}).json()["results"]
    assert any(r["kind"] == "rail" and r["refId"] == "sepa_inst" for r in res[:3])


def test_payment_seed_is_idempotent(client):
    from app.db import SessionLocal
    from app.payments import seed_payments

    with SessionLocal() as db:
        assert seed_payments(db) is False


def test_rail_reference_data_refreshes_on_older_databases(client):
    from app.db import SessionLocal
    from app.models import PaymentRail
    from app.payments import seed_payments

    with SessionLocal() as db:
        swift = db.get(PaymentRail, "swift")
        swift.changes = swift.changes[:1]  # as an older release would have stored it
        db.commit()
        assert seed_payments(db) is True
        db.refresh(swift)
        assert any("unstructured postal addresses" in c["text"] for c in swift.changes)
    swift_api = client.get("/api/payments/rails/swift").json()
    assert swift_api["changes"][0]["date"] == "2026-12"  # newest first
