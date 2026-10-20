"""Charter v1.3 items: structured protocol JSON + validation tool, hybrid rule, authority guard."""
from pathlib import Path

import pymupdf
import pytest

from protocol_review import protocol_json as pj
from protocol_review.graph import AuthorityViolation, guarded
from protocol_review.llm import MockLLM
from protocol_review.agents.mock_responses import NO_LLM_RESPONSES
from protocol_review.pdf_parser import parse_pdf
from protocol_review.pipeline import run_review
from protocol_review.scoring import hybrid_decision


def _f(i, sev, status):
    return {"id": f"X-{i}", "severity": sev, "status": status, "title": f"t{i}"}


# ---------------------------------------------------------------- item 1
def test_protocol_json_sections_and_validation(good_pdf):
    parsed = parse_pdf(good_pdf)
    doc = pj.build_protocol_json(parsed["pages"], parsed["protocol_meta"], good_pdf)
    heads = [s["heading"] for s in doc["sections"]]
    assert heads[0] == "Front matter"
    assert any(h.startswith("8. Sample Size") for h in heads) and any("Ethics" in h for h in heads)
    assert all(s["page_start"] <= s["page_end"] for s in doc["sections"])
    assert doc["source"]["sha256"] and doc["source"]["page_count"] == len(parsed["pages"])
    assert "".join(s["text"] for s in doc["sections"])  # original text preserved
    v = pj.validate_protocol_json(doc)
    assert v["valid"] and v["errors"] == []
    assert pj.section_for(doc, 1, "two intramuscular injections of VX-101 100 micrograms").startswith("3. Trial Design")
    assert pj.section_for(doc, None, "") == ""


def test_validation_tool_rejects_empty_pdf(tmp_path):
    empty = tmp_path / "empty.pdf"
    d = pymupdf.open(); d.new_page(); d.save(str(empty)); d.close()
    parsed = parse_pdf(empty)
    doc = pj.build_protocol_json(parsed["pages"], parsed["protocol_meta"], empty)
    v = pj.validate_protocol_json(doc)
    assert not v["valid"] and any("too little extractable text" in e for e in v["errors"])
    bad = dict(doc); bad["metadata"] = {**doc["metadata"], "nct_id": "NCT12"}
    assert any("malformed NCT" in e for e in pj.validate_protocol_json(bad)["errors"])


def test_graph_stops_at_validation_for_empty_pdf(tmp_path, registry_fetch):
    empty = tmp_path / "empty.pdf"
    d = pymupdf.open(); d.new_page(); d.save(str(empty)); d.close()
    llm = MockLLM(NO_LLM_RESPONSES)
    res = run_review(empty, source="test", llm=llm, registry_fetch=registry_fetch)
    assert res["validation"]["valid"] is False
    assert res["decision"] == "RETURNED_ADMIN"
    assert any(f["id"] == "ADM-V001" and f["category"] == "VALIDATION_FAILED" for f in res["findings"])
    assert [c["schema"] for c in llm.calls] == ["FinalSummary"]      # no review agent was called


# ---------------------------------------------------------------- item 5
def test_hybrid_rule_thresholds():
    assert hybrid_decision([], admin_ok=False)[0].value == "RETURNED_ADMIN"
    assert hybrid_decision([], admin_ok=True)[0].value == "PASS"
    d, why = hybrid_decision([_f(1, "critical", "verified")], True)
    assert d.value == "MAJOR_CONCERNS" and "critical" in why
    assert hybrid_decision([_f(1, "major", "verified")], True)[0].value == "PASS"                    # 90
    assert hybrid_decision([_f(1, "major", "verified"), _f(2, "minor", "verified")], True)[0].value == "NEEDS_HUMAN_REVIEW"  # 87
    assert hybrid_decision([_f(i, "major", "verified") for i in range(4)], True)[0].value == "MAJOR_CONCERNS"  # 60
    assert hybrid_decision([_f(1, "major", "unverified")], True)[0].value == "NEEDS_HUMAN_REVIEW"   # 100 but pending
    assert hybrid_decision([_f(1, "critical", "rejected"), _f(2, "critical", "withdrawn")], True)[0].value == "PASS"


# ---------------------------------------------------------------- item 4
def test_authority_guard_blocks_illegal_writes():
    ok = guarded("administrative", lambda s: {"admin_ok": True, "findings": [], "trace": []})
    assert ok({})["admin_ok"] is True
    bad = guarded("administrative", lambda s: {"decision": "PASS"})          # admin agent may not decide
    with pytest.raises(AuthorityViolation):
        bad({})
    tamper = guarded("scientific_critic", lambda s: {"protocol_json": {}})  # protocol data is immutable
    with pytest.raises(AuthorityViolation):
        tamper({})
    coord = guarded("finalize", lambda s: {"admin_report": {}})             # coordinator may not alter agent reports
    with pytest.raises(AuthorityViolation):
        coord({})
