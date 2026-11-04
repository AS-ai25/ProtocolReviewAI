"""Guideline-code validation in the deterministic evidence check (regression for the 2026-11-04 sub-item bug)."""
from protocol_review.agents import base
from protocol_review.knowledge_base import rule_codes

PAGES = [{"page": 1, "text": "Patients with a compliance rate below 80% are removed from the per-protocol analysis."}]
QUOTE = "compliance rate below 80% are removed from the per-protocol analysis"


def _v(ref):
    return base.verify_evidence({"id": "x", "guideline_ref": ref, "evidence": [{"page": 1, "quote": QUOTE}]}, PAGES, rule_codes())


def test_subitem_codes_are_valid_in_lower_and_upper_case():
    for ref in ("SPIRIT-27b", "SPIRIT-27B", "SPIRIT-14a", "SPIRIT-21a", "SPIRIT-28b; SPIRIT-28a"):
        assert _v(ref)["guideline_ref_valid"], ref
    assert _v("SPIRIT-19")["guideline_ref_valid"] and _v("GCP-07")["guideline_ref_valid"] and _v("ADMIN-CHK-06")["guideline_ref_valid"]


def test_unknown_or_missing_codes_are_invalid():
    for ref in ("SPIRIT-99", "SPIRIT-27z", "", "see SPIRIT"):
        assert not _v(ref)["guideline_ref_valid"], ref
    assert _v("SPIRIT-27b")["evidence_found"] == 1
