"""Re-scoring and the human-check sampler work from a saved run (skipped when the run outputs are not on disk)."""
import csv
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "eval"))

import make_human_check  # noqa: E402
import rescore  # noqa: E402

STAMP = "20261029-205913"
SUMMARY = ROOT / "eval" / "results" / f"ablation-{STAMP}.json"
OUTPUTS = ROOT / "outputs"          # the real run folder (conftest redirects OUTPUT_DIR to a temp dir)


def _outputs_present() -> bool:
    return SUMMARY.exists() and (OUTPUTS / f"abl-agents_full-nct01977547-{STAMP}" / "findings.json").exists()


@pytest.mark.skipif(not _outputs_present(), reason="live run outputs not on this machine")
def test_rescore_reproduces_the_live_table_and_the_scientific_view(tmp_path):
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    cases = rescore.load_cases(ROOT / "eval" / "labeled_cases", "nct*.json")
    rows = rescore.rescore(summary, cases, STAMP, outputs=OUTPUTS, rules_row=False)
    assert [r["key"] for r in rows] == [r["key"] for r in summary["rows"]]
    for new, old in zip(rows, summary["rows"]):
        # the predictions are the saved ones: verified / unverified counts, cost and runtime never change;
        # the matches may (the labels were corrected after the live run - see domain_correction in the files)
        assert (new["n_verified"], new["n_unverified"], new["labels"], new["llm_calls"], new["input_tokens"]) == \
               (old["n_verified"], old["n_unverified"], old["labels"], old["llm_calls"], old["input_tokens"])
    sci = rescore.rescore(summary, cases, STAMP, domain="scientific", outputs=OUTPUTS, rules_row=False)
    with_rules = rescore.rescore(summary, cases, STAMP, domain="scientific", outputs=OUTPUTS)
    assert with_rules[0]["key"] == "rules_only" and with_rules[0]["llm_calls"] == 0 and with_rules[0]["tp"] == 1   # row 0: rules alone
    n_sci = sum(1 for c in cases for x in c["expected_findings"] if x["domain"] == "scientific")
    assert all(r["labels"] == n_sci for r in sci) and n_sci == 37
    assert rescore.main(["--stamp", STAMP, "--out", str(tmp_path / "r.md"), "--note", "test", "--outputs", str(OUTPUTS),
                         "--results-dir", str(tmp_path / "res")]) == 0
    assert list((tmp_path / "res").glob("rescore-*.json"))
    md = (tmp_path / "r.md").read_text(encoding="utf-8")
    assert "Scientific domain only" in md and "Critic contribution" in md


@pytest.mark.skipif(not _outputs_present(), reason="live run outputs not on this machine")
def test_human_check_sampler_is_deterministic_and_stratified(tmp_path):
    out = tmp_path / "hc.csv"
    args = ["--stamp", STAMP, "--n", "10", "--outputs", str(OUTPUTS)]
    assert make_human_check.main([*args, "--out", str(out)]) == 0
    rows = list(csv.DictReader(out.open(encoding="utf-8")))
    assert len(rows) == 10 and len({r["case_id"] for r in rows}) == 5   # two per protocol
    assert all(int(r["page"]) > 0 and r["quote"] for r in rows)
    out2 = tmp_path / "hc2.csv"
    make_human_check.main([*args, "--out", str(out2)])
    assert out.read_text(encoding="utf-8") == out2.read_text(encoding="utf-8")
