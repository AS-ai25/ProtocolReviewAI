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
    rows = rescore.rescore(summary, cases, STAMP, outputs=OUTPUTS)
    assert [r["key"] for r in rows] == [r["key"] for r in summary["rows"]]
    for new, old in zip(rows, summary["rows"]):          # same labels -> same numbers as the live run
        assert (new["matched_verified"], new["n_verified"], new["tp"], new["labels"]) == \
               (old["matched_verified"], old["n_verified"], old["tp"], old["labels"])
    sci = rescore.rescore(summary, cases, STAMP, domain="scientific", outputs=OUTPUTS)
    assert all(r["labels"] == 21 for r in sci)
    assert rescore.main(["--stamp", STAMP, "--out", str(tmp_path / "r.md"), "--note", "test", "--outputs", str(OUTPUTS)]) == 0
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
