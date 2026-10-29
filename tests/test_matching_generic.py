"""Matching rule, charter v1.5 amendment: generic categories need the page as well."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "eval"))

from matching import GENERIC_CATEGORIES, matches, score_findings  # noqa: E402


def _f(domain, category, page=None, ref=""):
    d = {"domain": domain, "category": category, "guideline_ref": ref, "status": "verified"}
    if page is not None:
        d["page"] = page
    return d


def test_specific_category_matches_without_page():
    assert matches(_f("administrative", "MISSING_REGISTRY_ID"), _f("administrative", "MISSING_REGISTRY_ID", page=1))


def test_generic_category_needs_the_page():
    label = _f("scientific", "INTERNAL_CONTRADICTION", page=11)
    assert "INTERNAL_CONTRADICTION" in GENERIC_CATEGORIES
    assert not matches(_f("scientific", "INTERNAL_CONTRADICTION", page=30), label)
    assert not matches(_f("scientific", "INTERNAL_CONTRADICTION"), label)
    assert matches(_f("scientific", "INTERNAL_CONTRADICTION", page=12), label)


def test_generic_label_without_page_keeps_category_only_matching():
    label = _f("administrative", "MISSING_SECTION")        # synthetic labels carry no page
    assert matches(_f("administrative", "MISSING_SECTION", page=40), label)


def test_generic_category_still_matches_through_guideline_ref_and_page():
    label = _f("scientific", "OTHER", page=14, ref="SPIRIT-27b; SPIRIT-27c")
    assert matches(_f("scientific", "ANALYSIS_POPULATION_UNCLEAR", page=14, ref="SPIRIT-27b"), label)
    assert not matches(_f("scientific", "ANALYSIS_POPULATION_UNCLEAR", page=20, ref="SPIRIT-27b"), label)


def test_one_generic_prediction_does_not_cover_every_generic_label():
    labels = [_f("administrative", "OTHER", page=9), _f("administrative", "OTHER", page=27),
              _f("administrative", "OTHER", page=33)]
    s = score_findings(labels, [_f("administrative", "OTHER", page=27)])
    assert s["tp"] == 1 and s["n_labels"] == 3


def test_real_label_files_are_normalised():
    import json
    for p in sorted((ROOT / "eval" / "labeled_cases").glob("nct*.json")):
        c = json.loads(p.read_text(encoding="utf-8"))
        assert c["blind"] is True and c["labeler"]
        for x in c["expected_findings"]:
            assert "," not in x["category"], (p.name, x["category"])
            assert isinstance(x["page"], int) and 0 <= x["page"] < 200, (p.name, x["page"])
            assert not x["note"].startswith("{"), p.name
