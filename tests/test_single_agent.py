"""Single-Agent Baseline with a MockLLM (no network)."""
import sys
from pathlib import Path

from protocol_review import memory
from protocol_review.agents.mock_responses import NO_LLM_RESPONSES
from protocol_review.llm import MockLLM
from protocol_review.pipeline import run_single_agent
from protocol_review.state import SingleAgentReport

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "eval"))
from evaluate import score  # noqa: E402


def _finding(i, domain, title, page, quote, ref="SPIRIT-14", severity="major", category="OTHER"):
    return {"id": f"X-{i}", "domain": domain, "category": category, "severity": severity, "title": title,
            "description": title, "evidence": [{"page": page, "quote": quote}] if quote or page else [],
            "guideline_ref": ref, "recommendation": "", "status": "proposed", "critic_notes": "", "source": "llm"}


def _report(findings, admin_accepted=True):
    return {"admin_accepted": admin_accepted, "admin_summary": "admin ok", "scientific_summary": "sci ok",
            "findings": findings, "checklist": [{"code": "ADMIN-CHK-01", "satisfied": True, "note": ""}],
            "registry_comparison": [{"field": "enrollment", "protocol_value": "30,415", "registry_value": "30415", "match": True}],
            "open_questions": ["Who adjudicates endpoints?"], "executive_summary": "one-call summary",
            "recommendation": "forward to the committee"}


def test_single_call_receives_everything_and_returns_baseline_shape(flawed_pdf, registry_fetch):
    llm = MockLLM(NO_LLM_RESPONSES)
    res = run_single_agent(flawed_pdf, nct_id="NCT04470427", registry_fetch=registry_fetch, llm=llm)

    assert [c["schema"] for c in llm.calls] == ["SingleAgentReport"]       # exactly ONE LLM call
    user = llm.calls[0]["user"]
    assert "ADMIN-CHK-06" in user                                            # administrative KB
    assert "SPIRIT-" in user and "GCP-" in user                              # scientific KB
    assert "ClinicalTrials.gov record for NCT04470427" in user               # registry summary
    assert "Deterministic rule findings already produced" in user            # rule findings
    assert "=== PAGE 1 ===" in user                                          # protocol text with page markers

    assert res["mode"] == "single_agent"
    for key in ("run_id", "pdf_path", "protocol_meta", "registry", "findings", "decision", "final_summary", "cost", "paths"):
        assert key in res
    assert res["decision"] == "RETURNED_ADMIN"                               # rule findings include a blocking admin item
    assert all(f["source"] == "rule" and f["status"] == "verified" for f in res["findings"])
    assert Path(res["paths"]["result"]).exists() and Path(res["paths"]["findings"]).exists()
    assert res["cost"]["llm_calls"] == 1 and res["cost"]["by_agent"] == {"single_agent": 1}
    run = memory.get_run(res["run_id"])
    assert run["status"] == "done" and run["decision"] == "RETURNED_ADMIN" and run["source"] == "single_agent"
    s = score([{"domain": "administrative", "category": "MISSING_INSURANCE"}], res["findings"])  # scorable by evaluate.py
    assert s["tp"] == 1


def test_evidence_verification_without_a_critic(good_pdf, registry_fetch):
    llm = MockLLM({"SingleAgentReport": _report([
        _finding(1, "scientific", "Real quote", 1, "two intramuscular injections of VX-101 100 micrograms or saline placebo"),
        _finding(2, "scientific", "Hallucinated quote", 1, "this sentence does not exist anywhere in the protocol text"),
        _finding(3, "scientific", "Unknown guideline code", 1, "two intramuscular injections of VX-101 100 micrograms or saline placebo", ref="SPIRIT-99"),
        _finding(4, "administrative", "Absence claim", 0, "", ref="ADMIN-CHK-04", severity="info", category="MISSING_SECTION"),  # info: does not return the submission
    ])})
    res = run_single_agent(good_pdf, registry_fetch=registry_fetch, llm=llm, write=False)

    by_id = {f["id"]: f for f in res["findings"] if f["source"] == "llm"}
    assert set(by_id) == {"SCI-L001", "SCI-L002", "SCI-L003", "ADM-L001"}   # renumbered per domain
    assert by_id["SCI-L001"]["status"] == "verified"
    assert by_id["SCI-L002"]["status"] == "unverified" and "not located" in by_id["SCI-L002"]["critic_notes"]
    assert by_id["SCI-L003"]["status"] == "unverified" and "Guideline code" in by_id["SCI-L003"]["critic_notes"]
    assert by_id["ADM-L001"]["status"] == "verified"                         # nothing to locate, valid code
    assert res["admin_ok"] is True
    assert res["decision"] == "MAJOR_CONCERNS"                               # SCI-L001 is a verified major finding
    assert "one-call summary" in res["final_summary"] and "SCI-L001" in res["final_summary"]
    assert res["registry_comparison"][0]["field"] == "enrollment" and res["open_questions"]
    assert "paths" not in res


def test_agent_rejection_blocks_and_llm_failure_degrades(good_pdf, flawed_pdf, registry_fetch):
    # the agent says "not accepted" with a blocking critical admin finding -> RETURNED_ADMIN
    llm = MockLLM({"SingleAgentReport": _report([
        _finding(1, "administrative", "No insurance certificate", 0, "", ref="ADMIN-CHK-07", severity="critical", category="MISSING_DOCUMENT"),
    ], admin_accepted=False)})
    res = run_single_agent(good_pdf, registry_fetch=registry_fetch, llm=llm, write=False)
    assert res["decision"] == "RETURNED_ADMIN" and res["admin_ok"] is False

    # LLM failure -> deterministic findings only, error recorded, still a valid result
    llm = MockLLM({})
    res = run_single_agent(flawed_pdf, registry_fetch=registry_fetch, llm=llm, write=False)
    assert res["errors"] and res["errors"][0].startswith("single_agent")
    assert res["findings"] and all(f["source"] == "rule" for f in res["findings"])
    assert res["decision"] == "RETURNED_ADMIN"
    assert "LLM unavailable" in res["final_summary"]


def test_single_agent_schema_is_strict_compatible():
    from protocol_review.llm import strict_schema
    schema = strict_schema(SingleAgentReport)
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) >= {"admin_accepted", "findings", "executive_summary", "recommendation"}
