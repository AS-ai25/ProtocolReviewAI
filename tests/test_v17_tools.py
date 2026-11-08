"""v1.7: agent failure never ends in PASS (M1), deterministic evidence tools, tool calling (2', 3', 4')."""
import json
from pathlib import Path

from protocol_review import memory
from protocol_review.agents import base
from protocol_review.agents.mock_responses import NO_LLM_RESPONSES
from protocol_review.llm import MockLLM
from protocol_review.pipeline import run_review, run_single_agent
from protocol_review.tools import agent_tools, evidence_tools

REAL_QUOTE = "Respiratory infections caused by the target pathogen remain a major cause of morbidity"
PAGES = [{"page": 1, "text": "1. Background. Respiratory infections remain a major cause of morbidity.\n"
                             "A Data Safety Monitoring Board (DSMB) will review unblinded safety data every six months."},
         {"page": 2, "text": "2. Sample size. A total of 300 participants will be randomised 1:1 (n = 300). Power 0.9, alpha 0.05."},
         {"page": 3, "text": "Table of contents ....... 5\n4.6 STUDY PARTICIPANT DURATION ........ 7"}]


def _f(i, title, category="OTHER", page=1, quote=REAL_QUOTE, ref="SPIRIT-14a", status="proposed", domain="scientific"):
    return {"id": f"SCI-{i}", "domain": domain, "category": category, "severity": "major", "title": title, "description": title,
            "evidence": [{"page": page, "quote": quote}] if page else [], "guideline_ref": ref, "recommendation": "",
            "status": status, "critic_notes": "", "source": "llm"}


# ---------------------------------------------------------------- M1
def test_llm_failure_never_ends_in_pass_multi_agent(good_pdf, registry_fetch):
    res = run_review(good_pdf, source="test", llm=MockLLM({}), registry_fetch=registry_fetch)   # every LLM call fails
    assert res["agent_failures"] == ["administrative", "scientific_reviewer"]
    assert res["decision"] == "NEEDS_HUMAN_REVIEW" and "did not run" in res["decision_rationale"]
    assert res["final_summary"].startswith("WARNING: the following agent(s) did not run")
    assert "administrative" in res["final_summary"]
    run = memory.get_run(res["run_id"])
    assert run["decision"] == "NEEDS_HUMAN_REVIEW"


def test_llm_failure_never_ends_in_pass_single_agent(good_pdf, registry_fetch):
    res = run_single_agent(good_pdf, registry_fetch=registry_fetch, llm=MockLLM({}), write=False)
    assert res["agent_failures"] == ["single_agent"] and res["decision"] == "NEEDS_HUMAN_REVIEW"
    assert res["final_summary"].startswith("WARNING")


# ---------------------------------------------------------------- deterministic evidence tools
def test_absence_search_finds_the_topic_and_blocks_a_wrong_missing_claim():
    f = _f(1, "No data monitoring committee is described", category="NO_DATA_MONITORING", page=2, quote="Power 0.9, alpha 0.05")
    search = evidence_tools.absence_search(f, PAGES)
    assert 1 in search["found_pages"] and any("DSMB" in h["snippet"] for h in search["hits"])
    v = base.verify_evidence(f, PAGES, {"SPIRIT-14a", "SPIRIT-28a"})
    status, note = base.code_status(v)
    assert status is not None and "described on page(s)" in note


def test_mention_only_quote_is_not_evidence_of_absence():
    f = _f(2, "Sample size justification missing", category="UNJUSTIFIED_SAMPLE_SIZE", page=2, quote="A total of 300 participants will be randomised", ref="SPIRIT-19")
    assert evidence_tools.quote_is_mention_only(f)
    neg = _f(3, "Stopping rules not specified", category="NO_STOPPING_RULES", page=2, quote="Stopping rules are not specified in this protocol", ref="SPIRIT-15b")
    assert not evidence_tools.quote_is_mention_only(neg)


def test_guideline_code_must_fit_the_category():
    assert evidence_tools.guideline_fits_category(_f(4, "x", category="INCONSISTENT_PHASE", ref="SPIRIT-8")) is False
    assert evidence_tools.guideline_fits_category(_f(5, "x", category="INCONSISTENT_PHASE", ref="SPIRIT-12")) is True
    assert evidence_tools.guideline_fits_category(_f(6, "x", category="OTHER", ref="SPIRIT-8")) is None


def test_duplicates_are_rejected_not_deleted():
    a = _f(1, "Primary analysis population is contradictory (ITT vs per-protocol)", category="INTERNAL_CONTRADICTION", page=2)
    b = _f(2, "Primary analysis population contradictory: ITT versus per protocol", category="INTERNAL_CONTRADICTION", page=2)
    c = _f(3, "Blinding of outcome assessors not described", category="BLINDING_UNSPECIFIED", page=1)
    out, pairs = evidence_tools.merge_duplicates([a, b, c])
    assert pairs == [("SCI-2", "SCI-1")] and out[1]["status"] == "rejected" and "Duplicate of SCI-1" in out[1]["critic_notes"]
    assert len(out) == 3 and out[2]["status"] == "proposed"


def test_numbers_table_and_study_design():
    table = evidence_tools.numbers_table(PAGES)
    assert table["sample_sizes"] and table["sample_sizes"][0]["n"] == 300
    d = evidence_tools.study_design(PAGES)
    assert d["randomised"] is True and "SPIRIT-21a" not in d["non_applicable_spirit_items"]
    obs = evidence_tools.study_design([{"page": 1, "text": "A retrospective observational cohort study of existing medical records."}])
    assert obs["observational"] and "SPIRIT-21a" in obs["non_applicable_spirit_items"]
    assert "Numbers table" in evidence_tools.numbers_prompt(table) and "do NOT apply" in evidence_tools.design_prompt(obs)


def test_rule_quotes_skip_contents_lines():
    from protocol_review.tools import checks
    page, quote = checks._find(PAGES, r"\bSTUDY PARTICIPANT DURATION\b")
    assert page == 3 and checks._is_toc_like(quote)      # a contents line is still returned when it is the only hit (fallback)
    page2, quote2 = checks._find(PAGES, r"\b300\b")
    assert page2 == 2 and quote2.startswith("A total of 300") and quote2.endswith(".")


# ---------------------------------------------------------------- tool calling
def test_agent_tools_executor():
    pj = {"sections": [{"number": "2", "title": "Sample size", "page_start": 2, "page_end": 2, "text": PAGES[1]["text"]}]}
    reg = {"found": True, "nct_id": "NCT1", "title": "T", "phase": "3", "status": "COMPLETED", "enrollment": 300,
           "conditions": ["x"], "interventions": ["a"], "primary_outcomes": ["o"], "sponsor": "S"}
    run = agent_tools.make_executor(PAGES, pj, reg)
    assert "p.1 [DSMB]" in run("search_protocol", {"query": "DSMB | monitoring board"})
    assert "no occurrence" in run("search_protocol", {"query": "zzqx"})
    assert run("get_page", {"page": 2}).startswith("=== PAGE 2") and "does not exist" in run("get_page", {"page": 9})
    assert "SECTION 2 Sample size" in run("get_section", {"name": "sample"})
    assert json.loads(run("registry_field", {"name": "enrollment"})) == {"enrollment": 300}
    assert "SPIRIT-19" in run("kb_lookup", {"code": "SPIRIT-19"}) and "not defined" in run("kb_lookup", {"code": "SPIRIT-99"})
    pc = json.loads(run("power_calc", {"p1": 0.12, "p2": 0.18, "alpha": 0.05, "power": 0.9, "dropout": 0.034}))
    assert 650 <= pc["n_per_arm"] <= 800 and pc["n_total_with_dropout"] > pc["n_total"]
    assert "bad arguments" in run("get_page", {"nope": 1}) and "unknown tool" in run("fly", {})


def test_tool_use_configuration_runs_tools_and_records_them(good_pdf, registry_fetch):
    sci = {"summary": "s", "registry_comparison": [], "open_questions": [],
           "findings": [_f(1, "Real quote", page=1, quote=REAL_QUOTE)]}
    critic = {"summary": "c", "verdicts": [{"finding_id": "SCI-L001", "verdict": "verified", "notes": "ok", "revised_severity": None}],
              "missed_issues": [], "proposed_memory": []}
    llm = MockLLM({**NO_LLM_RESPONSES, "ScientificReport": sci, "CriticReport": critic,
                   "ScientificReport__tool_calls": [{"name": "search_protocol", "input": {"query": "sample size"}}, {"name": "kb_lookup", "input": {"code": "SPIRIT-19"}}],
                   "CriticReport__tool_calls": [{"name": "get_page", "input": {"page": 1}}, {"name": "registry_field", "input": {"name": "enrollment"}}]})
    res = run_review(good_pdf, source="test", llm=llm, registry_fetch=registry_fetch, tool_use=True)
    assert res["tool_use"] is True and res["study_design"]["kind"] and res["numbers_table"]
    calls = {c["schema"]: c for c in llm.calls}
    assert len(calls["ScientificReport"]["tool_calls"]) == 2 and len(calls["CriticReport"]["tool_calls"]) == 2
    assert len(calls["AdminReport"].get("tool_calls", [])) == 0      # the administrative agent has no tools
    recorded = [i for i in memory.list_interactions(res["run_id"]) if i.get("tool_calls")]
    assert {i["agent"] for i in recorded} == {"scientific_reviewer", "scientific_critic"}
    assert any(m["content"].startswith("TOOL USE") for m in memory.get_messages(res["run_id"]))


def test_single_agent_with_tools(good_pdf, registry_fetch):
    report = {"admin_accepted": True, "admin_summary": "a", "scientific_summary": "s", "checklist": [], "registry_comparison": [],
              "open_questions": [], "executive_summary": "e", "recommendation": "r", "findings": [_f(1, "Real quote", page=1, quote=REAL_QUOTE)]}
    llm = MockLLM({"SingleAgentReport": report, "SingleAgentReport__tool_calls": [{"name": "power_calc", "input": {"p1": 0.1, "p2": 0.2}}]})
    res = run_single_agent(good_pdf, registry_fetch=registry_fetch, llm=llm, write=False, tools=True)
    assert res["mode"] == "single_agent_tools" and len(llm.calls[0]["tool_calls"]) == 1
    assert "Tools" in llm.calls[0]["user"]
