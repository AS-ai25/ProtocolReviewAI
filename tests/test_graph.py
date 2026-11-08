"""End-to-end graph runs with a MockLLM (no network)."""
import json
from pathlib import Path

from protocol_review import memory
from protocol_review.agents.mock_responses import NO_LLM_RESPONSES
from protocol_review.llm import MockLLM
from protocol_review.pipeline import run_review


def _sci_finding(i, title, page, quote, ref="SPIRIT-14a", severity="major"):
    return {"id": f"SCI-{i}", "domain": "scientific", "category": "OTHER", "severity": severity, "title": title,
            "description": title, "evidence": [{"page": page, "quote": quote}], "guideline_ref": ref,
            "recommendation": "", "status": "proposed", "critic_notes": "", "source": "llm"}


def test_flawed_protocol_is_returned_at_admin_stage(flawed_pdf, registry_fetch):
    llm = MockLLM(NO_LLM_RESPONSES)
    res = run_review(flawed_pdf, source="test", submitter="pytest", llm=llm, registry_fetch=registry_fetch)
    assert res["decision"] == "RETURNED_ADMIN"
    assert res["admin_ok"] is False
    assert res["score"]["scope"] == "administrative_only" and res["score"]["score"] < 100
    assert "Score:" in Path(res["report_paths"]["final_report"]).read_text(encoding="utf-8")
    assert res.get("scientific_report") is None       # scientific agents never ran
    sci_rule = [f for f in res["findings"] if f["domain"] == "scientific"]
    assert sci_rule and all(f["source"] == "rule" and f["status"] == "verified" for f in sci_rule)  # free checks still reported
    assert {c["schema"] for c in llm.calls} == {"AdminReport", "FinalSummary"}
    assert Path(res["report_paths"]["final_report"]).exists()
    assert Path(res["report_paths"]["administrative_report"]).exists()
    assert res["notifications"] and "dry-run" in res["notifications"][0]
    assert (Path(res["report_paths"]["final_report"]).parent / "email.eml").exists()
    run = memory.get_run(res["run_id"])
    assert run["status"] == "done" and run["decision"] == "RETURNED_ADMIN"
    msgs = memory.get_messages(res["run_id"])
    assert [m["agent"] for m in msgs][:3] == ["coordinator", "coordinator", "administrative"]  # intake, validation, admin
    assert res["validation"]["valid"] is True
    assert res["decision_rationale"].startswith("administrative part")
    assert Path(res["report_paths"]["final_report_pdf"]).stat().st_size > 1000          # PDF rendered
    assert Path(res["report_paths"]["protocol_json"]).exists()
    assert all(f.get("section") for f in res["findings"] if f["source"] == "rule" and f["evidence"])  # sections attached


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
        f1 = _sci_finding(1, "Real quote finding", 1, "two intramuscular injections of VX-101 100 micrograms or saline placebo")
        f2 = _sci_finding(2, "Revised finding", 2, "Independent audits occur annually", severity="minor")
        f1["id"], f2["id"] = "SCI-L001", "SCI-L002"                       # reviewer keeps the ids it was given
        return {"summary": "revised", "registry_comparison": [], "open_questions": [], "findings": [f1, f2]}

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
    assert by_id["SCI-L003"]["status"] == "withdrawn"  # append-only: dropped findings are kept, not deleted
    assert len(res["scientific_reports"]) == 2 and len(res["critic_reports"]) == 2   # one report per round
    assert res["critic_reports"][0]["round"] == 0 and res["critic_reports"][1]["round"] == 1
    # hybrid rule: no critical; score = 100 - 10 (major) - 3 (minor) = 87 -> NEEDS_HUMAN_REVIEW
    assert res["score"]["score"] == 87
    assert res["decision"] == "NEEDS_HUMAN_REVIEW" and "87" in res["decision_rationale"]
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
