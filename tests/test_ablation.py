"""Checkpoint 2 evaluation modes: gate bypass, critic ablation, single-agent verification ablation,
the locked matching rule and the ablation runner (dry mode, no network)."""
import sys
from pathlib import Path

from protocol_review.agents.mock_responses import NO_LLM_RESPONSES
from protocol_review.llm import MockLLM
from protocol_review.pipeline import run_review, run_single_agent

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "eval"))
import ablation  # noqa: E402
from matching import matches, score_findings  # noqa: E402

REAL_QUOTE = "Respiratory infections caused by the target pathogen remain a major cause of morbidity"
FAKE_QUOTE = "this sentence does not exist anywhere in the protocol text"


def _sci(i, title, quote, page=1, ref="SPIRIT-14a", status="proposed", category="OTHER"):
    return {"id": f"SCI-{i}", "domain": "scientific", "category": category, "severity": "major", "title": title,
            "description": title, "evidence": [{"page": page, "quote": quote}], "guideline_ref": ref,
            "recommendation": "", "status": status, "critic_notes": "", "source": "llm"}


SCI_REPORT = {"summary": "s", "registry_comparison": [], "open_questions": [],
              "findings": [_sci(1, "Real quote", REAL_QUOTE), _sci(2, "Hallucinated", FAKE_QUOTE)]}


# ------------------------------------------------------------ 1. gate bypass
def test_force_scientific_runs_scientific_stage_but_decision_stays_returned_admin(flawed_pdf, registry_fetch):
    llm = MockLLM({**NO_LLM_RESPONSES, "ScientificReport": SCI_REPORT,
                   "CriticReport": {"summary": "c", "verdicts": [
                       {"finding_id": "SCI-L001", "verdict": "verified", "notes": "ok", "revised_severity": None},
                       {"finding_id": "SCI-L002", "verdict": "verified", "notes": "ok", "revised_severity": None}],
                       "missed_issues": [], "proposed_memory": []}})
    res = run_review(flawed_pdf, source="test", llm=llm, registry_fetch=registry_fetch, force_scientific=True)
    assert res["admin_ok"] is False
    assert res["decision"] == "RETURNED_ADMIN"                      # hybrid rule unchanged
    assert [c["schema"] for c in llm.calls] == ["AdminReport", "ScientificReport", "CriticReport", "FinalSummary"]
    assert res["scientific_report"] is not None and res["critic_report"] is not None
    by_id = {f["id"]: f for f in res["findings"] if f["source"] == "llm"}
    assert by_id["SCI-L001"]["status"] == "verified"
    assert by_id["SCI-L002"]["status"] == "unverified"              # guardrail still applies
    assert res["score"]["scope"] == "full_forced"
    assert "forced for evaluation" in Path(res["report_paths"]["final_report"]).read_text(encoding="utf-8")
    assert Path(res["report_paths"]["scientific_report"]).exists()
    assert res["force_scientific"] is True

    # without the switch nothing changes (regression)
    llm2 = MockLLM({**NO_LLM_RESPONSES, "ScientificReport": SCI_REPORT})
    res2 = run_review(flawed_pdf, source="test", llm=llm2, registry_fetch=registry_fetch)
    assert [c["schema"] for c in llm2.calls] == ["AdminReport", "FinalSummary"] and res2.get("scientific_report") is None


# ------------------------------------------------------------ 2. critic ablation
def test_no_critic_skips_the_critic_and_verifies_by_code_only(good_pdf, registry_fetch):
    llm = MockLLM({**NO_LLM_RESPONSES, "ScientificReport": SCI_REPORT,
                   "CriticReport": {"summary": "MUST NOT BE CALLED", "verdicts": [], "missed_issues": [], "proposed_memory": []}})
    res = run_review(good_pdf, source="test", llm=llm, registry_fetch=registry_fetch, no_critic=True)
    assert [c["schema"] for c in llm.calls] == ["AdminReport", "ScientificReport", "FinalSummary"]
    assert res.get("critic_report") is None and res["critic_reports"] == [] and res["revise_rounds"] == 0
    by_id = {f["id"]: f for f in res["findings"] if f["source"] == "llm"}
    assert by_id["SCI-L001"]["status"] == "verified" and "no independent critic" in by_id["SCI-L001"]["critic_notes"]
    assert by_id["SCI-L002"]["status"] == "unverified" and "not located" in by_id["SCI-L002"]["critic_notes"]
    assert res["decision"] == "NEEDS_HUMAN_REVIEW"                  # 1 major verified (90) + 1 unverified
    assert any(t["event"] == "code_only_verification" for t in res["trace"])


# ------------------------------------------------------------ 2b. single-agent verification ablation
def test_single_agent_no_verification_keeps_the_models_status(good_pdf, registry_fetch):
    report = {"admin_accepted": True, "admin_summary": "a", "scientific_summary": "s", "checklist": [],
              "registry_comparison": [], "open_questions": [], "executive_summary": "e", "recommendation": "r",
              "findings": [_sci(1, "Real quote", REAL_QUOTE), _sci(2, "Hallucinated", FAKE_QUOTE),
                           _sci(3, "Model doubts itself", FAKE_QUOTE, status="unverified")]}
    off = run_single_agent(good_pdf, registry_fetch=registry_fetch, llm=MockLLM({"SingleAgentReport": report}), write=False, verify=False)
    on = run_single_agent(good_pdf, registry_fetch=registry_fetch, llm=MockLLM({"SingleAgentReport": report}), write=False, verify=True)
    st_off = {f["id"]: f["status"] for f in off["findings"] if f["source"] == "llm"}
    st_on = {f["id"]: f["status"] for f in on["findings"] if f["source"] == "llm"}
    assert st_off == {"SCI-L001": "verified", "SCI-L002": "verified", "SCI-L003": "unverified"}   # hallucination passes
    assert st_on == {"SCI-L001": "verified", "SCI-L002": "unverified", "SCI-L003": "unverified"}  # code catches it
    assert off["mode"] == "single_agent_no_verification" and on["mode"] == "single_agent"


# ------------------------------------------------------------ 3. matching rule (charter v1.4)
def test_matching_rule_domain_alias_or_ref_and_page():
    label = {"domain": "scientific", "category": "NO_STATISTICAL_PLAN", "guideline_ref": "SPIRIT-20", "page": 4}
    assert matches({"domain": "scientific", "category": "NO_STATISTICAL_PLAN"}, label)
    assert matches({"domain": "scientific", "category": "MISSING_SAP"}, label)                      # alias
    assert not matches({"domain": "administrative", "category": "NO_STATISTICAL_PLAN"}, label)      # domain differs
    assert matches({"domain": "scientific", "category": "OTHER", "guideline_ref": "SPIRIT-20", "evidence": [{"page": 5, "quote": "x"}]}, label)
    assert not matches({"domain": "scientific", "category": "OTHER", "guideline_ref": "SPIRIT-20", "evidence": [{"page": 7, "quote": "x"}]}, label)
    assert not matches({"domain": "scientific", "category": "OTHER", "guideline_ref": "SPIRIT-21", "evidence": [{"page": 4, "quote": "x"}]}, label)

    labels = [label, {"domain": "administrative", "category": "MISSING_INSURANCE"}]
    preds = [{"domain": "scientific", "category": "MISSING_SAP", "status": "verified"},
             {"domain": "scientific", "category": "OTHER", "status": "verified"},        # unlabeled claim
             {"domain": "administrative", "category": "NO_INSURANCE", "status": "unverified"},
             {"domain": "scientific", "category": "NO_STATISTICAL_PLAN", "status": "rejected"}]   # not a prediction
    s = score_findings(labels, preds)
    assert s["n_verified"] == 2 and s["matched_verified"] == 1 and s["verified_precision"] == 0.5
    assert s["coverage"] == 1.0 and s["n_unverified"] == 1 and s["tp"] == 2 and s["fp"] == 1 and s["fn"] == 0


# ------------------------------------------------------------ 4. ablation runner, dry mode
def test_ablation_dry_run_writes_the_configuration_table(tmp_path, registry_fetch):
    out = tmp_path / "results.md"
    summary = ablation.run_ablation(ROOT / "eval" / "labeled_cases", out, no_llm=True, registry_fetch=registry_fetch,
                                    results_dir=tmp_path / "results", pattern="synthetic_*.json")
    assert [r["key"] for r in summary["rows"]] == ["single_no_verification", "single_verified", "agents_no_critic", "agents_full",
                                                   "single_tools", "agents_no_critic_tools", "agents_full_tools"]   # v1.7: 2' 3' 4'
    md = out.read_text(encoding="utf-8")
    table = md.split("## Ablation table")[1].split("## Per case")[0]
    data_rows = [ln for ln in table.splitlines() if ln.startswith("| ") and not ln.startswith("| #")]
    assert len(data_rows) == 7 and data_rows[4].startswith("| 2' |")       # the v1.7 rows carry primed numbers
    assert "DRY RUN" in md
    for r in summary["rows"]:
        assert r["coverage"] == 1.0                      # rule findings cover every injected deficiency
        assert r["n_unverified"] == 0 and r["llm_calls"] >= 1
    assert list((tmp_path / "results").glob("ablation-nollm-*.json"))
    # the CLI entry point accepts the documented flags
    assert ablation.main(["--no-llm", "--no-registry", "--out", str(tmp_path / "cli.md"), "--results-dir", str(tmp_path / "r2"),
                          "--only", "single_verified", "--cases-glob", "synthetic_*.json"]) == 0
    assert (tmp_path / "cli.md").exists()


def test_model_comparison_rows_are_opt_in_and_restore_the_model(tmp_path, registry_fetch):
    """Mentor M8: the Sonnet / Haiku rows run only when named, record their model and leave the settings untouched."""
    from protocol_review.config import settings
    before = (settings.llm_model, settings.llm_fallbacks)
    summary = ablation.run_ablation(ROOT / "eval" / "labeled_cases", tmp_path / "results.md", no_llm=True, registry_fetch=registry_fetch,
                                    results_dir=tmp_path / "results", pattern="synthetic_*.json", only=["agents_full_haiku"])
    assert [r["key"] for r in summary["rows"]] == ["agents_full_haiku"] and summary["rows"][0]["model"] == "mock"
    assert (settings.llm_model, settings.llm_fallbacks) == before
    assert {c["key"] for c in ablation.MODEL_CONFIGS} == {"agents_full_v17", "agents_full_sonnet", "agents_full_haiku"}
    assert ablation.ROW_NUM["agents_full_sonnet"] == "4-S"
