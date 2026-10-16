"""End-to-end graph runs with a MockLLM (no network)."""
import json
from pathlib import Path

from protocol_review import memory
from protocol_review.agents.mock_responses import NO_LLM_RESPONSES
from protocol_review.llm import MockLLM
from protocol_review.pipeline import run_review


def _sci_finding(i, title, page, quote, ref="SPIRIT-14", severity="major"):
    return {"id": f"SCI-{i}", "domain": "scientific", "category": "OTHER", "severity": severity, "title": title,
            "description": title, "evidence": [{"page": page, "quote": quote}], "guideline_ref": ref,
            "recommendation": "", "status": "proposed", "critic_notes": "", "source": "llm"}


def _adm_finding(i, title, page, quote, ref="ADMIN-CHK-04", severity="major", category="MISSING_SECTION"):
    return {"id": f"ADM-{i}", "domain": "administrative", "category": category, "severity": severity, "title": title,
            "description": title, "evidence": [{"page": page, "quote": quote}], "guideline_ref": ref,
            "recommendation": "", "status": "proposed", "critic_notes": "", "source": "llm"}


def _admin_report(findings, accepted=True):
    return {"accepted": accepted, "summary": "admin summary", "findings": findings, "checklist": []}


def _critic_report(verdicts, missed=None, proposed=None, summary="critic"):
    return {"summary": summary, "missed_issues": missed or [], "proposed_memory": proposed or [],
            "verdicts": [{"finding_id": fid, "verdict": verdict, "notes": notes, "revised_severity": sev}
                         for fid, verdict, notes, sev in verdicts]}


def _audited_ids(user):
    return [f["id"] for f in json.loads(user.split("# Findings to audit (return one verdict per id)\n")[1].split("\n\n# Deterministic")[0])]


def test_flawed_protocol_is_returned_at_admin_stage(flawed_pdf, registry_fetch):
    llm = MockLLM(NO_LLM_RESPONSES)
    res = run_review(flawed_pdf, source="test", submitter="pytest", llm=llm, registry_fetch=registry_fetch)
    assert res["decision"] == "RETURNED_ADMIN"
    assert res["admin_ok"] is False
    assert res.get("scientific_report") is None       # scientific agents never ran
    # the admin critic has nothing to audit (no LLM admin findings in NO_LLM mode) -> no LLM call
    assert {c["schema"] for c in llm.calls} == {"AdminReport", "FinalSummary"}
    assert res["admin_critic_report"]["summary"] == "No LLM findings to audit."
    assert Path(res["report_paths"]["final_report"]).exists()
    assert Path(res["report_paths"]["administrative_report"]).exists()
    assert res["notifications"] and "dry-run" in res["notifications"][0]
    assert (Path(res["report_paths"]["final_report"]).parent / "email.eml").exists()
    run = memory.get_run(res["run_id"])
    assert run["status"] == "done" and run["decision"] == "RETURNED_ADMIN"
    msgs = memory.get_messages(res["run_id"])
    assert [m["agent"] for m in msgs][:2] == ["coordinator", "administrative"]


def test_admin_critic_revision_round_and_recomputed_acceptance(good_pdf, registry_fetch):
    """Admin agent proposes 3 findings; the admin critic verifies one, asks to revise one and wrongly
    'verifies' a hallucinated one (guardrail -> unverified). Round 2: the agent escalates the revised
    finding to critical, the critic verifies it -> the submission is RETURNED_ADMIN although the agent
    said `accepted`; the scientific agents never run; a lesson is proposed for HITL approval."""
    real = "two intramuscular injections of VX-101 100 micrograms or saline placebo"
    rounds = {"n": 0}

    def admin(system, user):
        rounds["n"] += 1
        if rounds["n"] == 1:
            assert "REVISION ROUND" not in user
            return _admin_report([
                _adm_finding(1, "Real quote", 1, real, severity="minor"),
                _adm_finding(2, "Needs revision", 2, "Independent audits occur annually"),
                _adm_finding(3, "Hallucinated", 1, "this sentence does not exist anywhere in the protocol text"),
            ])
        assert "REVISION ROUND - administrative critic feedback" in user and "ADM-L002" in user
        return _admin_report([
            _adm_finding(1, "Real quote", 1, real, severity="minor"),
            _adm_finding(2, "Insurance certificate missing", 2, "Independent audits occur annually",
                         ref="ADMIN-CHK-07", severity="critical", category="MISSING_INSURANCE"),
            _adm_finding(3, "Hallucinated", 1, "this sentence does not exist anywhere in the protocol text"),
        ])

    def critic(system, user):
        assert "Administrative checklist (knowledge base)" in user
        ids = _audited_ids(user)
        assert ids == ["ADM-L001", "ADM-L002", "ADM-L003"]
        if "Needs revision" in user:
            return _critic_report([("ADM-L001", "verified", "quote confirmed", None),
                                   ("ADM-L002", "revise", "which document is missing? cite the ADMIN-CHK code", None),
                                   ("ADM-L003", "verified", "looks fine", None)],
                                  proposed=["Check that the insurance certificate names the sponsor."])
        return _critic_report([("ADM-L001", "verified", "ok", None),
                               ("ADM-L002", "verified", "insurance really missing", None),
                               ("ADM-L003", "verified", "still looks fine", None)])

    llm = MockLLM({**NO_LLM_RESPONSES, "AdminReport": admin, "AdminCriticReport": critic})
    res = run_review(good_pdf, source="test", submitter="pytest", llm=llm, registry_fetch=registry_fetch)

    assert [c["schema"] for c in llm.calls] == ["AdminReport", "AdminCriticReport", "AdminReport", "AdminCriticReport", "FinalSummary"]
    assert res["admin_revise_rounds"] == 1
    by_id = {f["id"]: f for f in res["findings"]}
    assert by_id["ADM-L001"]["status"] == "verified"
    assert by_id["ADM-L002"]["status"] == "verified" and by_id["ADM-L002"]["severity"] == "critical"
    assert by_id["ADM-L003"]["status"] == "unverified" and "not located" in by_id["ADM-L003"]["critic_notes"]  # guardrail
    assert res["admin_report"]["accepted_by_agent"] is True
    assert res["admin_ok"] is False and res["admin_report"]["blocking_findings"] == ["ADM-L002"]
    assert res["decision"] == "RETURNED_ADMIN"
    assert res.get("scientific_report") is None
    assert res["cost"]["by_agent"] == {"administrative": 2, "administrative_critic": 2, "coordinator": 1}
    proposals = memory.list_memories(status="proposed", agent="administrative_critic")
    assert any("insurance certificate" in p["fact"] for p in proposals)
    report = Path(res["report_paths"]["administrative_report"]).read_text(encoding="utf-8")
    assert "Administrative critic" in report and "ADM-L002" in report


def test_admin_critic_rejects_and_escalates_missed_issues_to_humans(good_pdf, registry_fetch):
    """Rejected findings disappear from the decision; an issue the critic says was MISSED becomes a
    revision request first and, after the last round, an UNVERIFIED finding for a human."""
    real = "two intramuscular injections of VX-101 100 micrograms or saline placebo"
    llm = MockLLM({**NO_LLM_RESPONSES,
                   "AdminReport": _admin_report([_adm_finding(1, "Duplicate of a rule finding", 1, real)]),
                   "AdminCriticReport": _critic_report([("ADM-L001", "rejected", "duplicates ADM-001", None)],
                                                       missed=["Appendix B is referenced on p. 2 but not attached"])})
    res = run_review(good_pdf, source="test", llm=llm, registry_fetch=registry_fetch)

    # NO_LLM scientific reviewer proposes nothing -> the scientific critic has nothing to audit (no call)
    assert [c["schema"] for c in llm.calls] == ["AdminReport", "AdminCriticReport", "AdminReport", "AdminCriticReport",
                                                "ScientificReport", "FinalSummary"]
    by_id = {f["id"]: f for f in res["findings"]}
    assert by_id["ADM-L001"]["status"] == "rejected"
    assert by_id["ADM-C001"]["status"] == "unverified" and "Appendix B" in by_id["ADM-C001"]["description"]
    assert res["admin_ok"] is True                        # rejected findings never block
    assert res["decision"] == "NEEDS_HUMAN_REVIEW"        # the missed issue waits for a human


def test_full_flow_with_critic_revision_round(good_pdf, registry_fetch):
    """Reviewer proposes 3 findings; critic verifies one, asks to revise one, rejects one;
    reviewer re-emits; critic verifies on round 2; memory lesson is proposed (not approved)."""
    round_holder = {"n": 0}

    def sci(system, user):
        round_holder["n"] += 1
        if round_holder["n"] == 1:
            return {"summary": "first pass", "registry_comparison": [
                {"field": "enrollment", "protocol_value": "30,415", "registry_value": "30415", "match": True}],
                "open_questions": ["Who adjudicates endpoints?"], "findings": [
                    _sci_finding(1, "Real quote finding", 1, "two intramuscular injections of VX-101 100 micrograms or saline placebo"),
                    _sci_finding(2, "Needs revision", 2, "Independent audits occur annually"),
                    _sci_finding(3, "Hallucinated", 1, "this sentence does not exist anywhere in the protocol text"),
                ]}
        assert "REVISION ROUND" in user and "SCI-L002" in user
        return {"summary": "revised", "registry_comparison": [], "open_questions": [], "findings": [
            _sci_finding(1, "Real quote finding", 1, "two intramuscular injections of VX-101 100 micrograms or saline placebo"),
            _sci_finding(2, "Revised finding", 2, "Independent audits occur annually", severity="minor"),
        ]}

    def critic(system, user):
        ids = [f["id"] for f in json.loads(user.split("# Findings to audit (return one verdict per id)\n")[1].split("\n\n# Deterministic")[0])]
        if "SCI-L003" in ids:
            return {"summary": "round 1", "verdicts": [
                {"finding_id": "SCI-L001", "verdict": "verified", "notes": "quote confirmed", "revised_severity": None},
                {"finding_id": "SCI-L002", "verdict": "revise", "notes": "add the page where auditing frequency is stated", "revised_severity": None},
                {"finding_id": "SCI-L003", "verdict": "verified", "notes": "looks fine", "revised_severity": None},
            ], "missed_issues": [], "proposed_memory": ["Always check that interim analyses have stopping boundaries."]}
        return {"summary": "round 2", "verdicts": [
            {"finding_id": "SCI-L001", "verdict": "verified", "notes": "ok", "revised_severity": None},
            {"finding_id": "SCI-L002", "verdict": "verified", "notes": "ok now", "revised_severity": "minor"},
        ], "missed_issues": [], "proposed_memory": []}

    llm = MockLLM({**NO_LLM_RESPONSES, "ScientificReport": sci, "CriticReport": critic,
                   "FinalSummary": {"executive_summary": "done", "key_findings": ["SCI-L001"], "recommendation": "forward"}})
    res = run_review(good_pdf, source="test", submitter="pytest", llm=llm, registry_fetch=registry_fetch)

    assert res["admin_ok"] is True
    assert res["revise_rounds"] == 1
    schemas = [c["schema"] for c in llm.calls]
    assert schemas == ["AdminReport", "ScientificReport", "CriticReport", "ScientificReport", "CriticReport", "FinalSummary"]
    by_id = {f["id"]: f for f in res["findings"]}
    assert by_id["SCI-L001"]["status"] == "verified"
    assert by_id["SCI-L002"]["status"] == "verified" and by_id["SCI-L002"]["severity"] == "minor"
    assert "SCI-L003" not in by_id                      # withdrawn by the reviewer in round 2
    assert res["decision"] == "MAJOR_CONCERNS"           # SCI-L001 is a verified major finding
    assert "done" in res["final_summary"]
    proposals = memory.list_memories(status="proposed", agent="scientific_critic")
    assert any("stopping boundaries" in p["fact"] for p in proposals)
    assert memory.recall_memories("scientific_critic") == []   # not approved -> not injected
    cost = res["cost"]
    assert cost["llm_calls"] == 6 and cost["by_agent"]["scientific_reviewer"] == 2
    assert Path(res["report_paths"]["scientific_report"]).read_text(encoding="utf-8").count("SCI-L001") >= 1


def test_guardrail_critic_cannot_verify_missing_quote(good_pdf, registry_fetch):
    llm = MockLLM({**NO_LLM_RESPONSES,
                   "ScientificReport": {"summary": "s", "registry_comparison": [], "open_questions": [], "findings": [
                       _sci_finding(1, "Hallucinated", 1, "this sentence does not exist anywhere in the protocol text")]},
                   "CriticReport": {"summary": "c", "verdicts": [
                       {"finding_id": "SCI-L001", "verdict": "verified", "notes": "fine", "revised_severity": None}],
                       "missed_issues": ["Check the DSMB charter (p. 2)"], "proposed_memory": []}})
    res = run_review(good_pdf, source="test", llm=llm, registry_fetch=registry_fetch)
    by_id = {f["id"]: f for f in res["findings"]}
    assert by_id["SCI-L001"]["status"] == "unverified"
    assert any(f["id"].startswith("SCI-C") and f["status"] == "unverified" for f in res["findings"])  # missed issue -> human
    assert res["decision"] == "NEEDS_HUMAN_REVIEW"


def test_llm_failure_degrades_gracefully(flawed_pdf, registry_fetch):
    llm = MockLLM({})  # every call raises LLMError
    res = run_review(flawed_pdf, source="test", llm=llm, registry_fetch=registry_fetch)
    assert res["decision"] == "RETURNED_ADMIN"
    assert any(e.startswith("administrative") for e in res["errors"])
    assert "Rule-based" not in res["final_summary"] or res["final_summary"]
