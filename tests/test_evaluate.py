import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "eval"))
from evaluate import score  # noqa: E402


def test_score_ignores_rejected_and_matches_on_domain_category():
    expected = [{"domain": "scientific", "category": "A"}, {"domain": "administrative", "category": "B"}]
    predicted = [
        {"domain": "scientific", "category": "A", "status": "verified"},
        {"domain": "scientific", "category": "C", "status": "rejected"},     # ignored
        {"domain": "scientific", "category": "D", "status": "unverified"},   # false positive
    ]
    s = score(expected, predicted)
    assert (s["tp"], s["fp"], s["fn"]) == (1, 1, 1)
    assert s["precision"] == 0.5 and s["recall"] == 0.5 and s["f1"] == 0.5
    empty = score([], [])
    assert {k: empty[k] for k in ("tp", "fp", "fn", "precision", "recall", "f1", "missed", "extra")} ==         {"tp": 0, "fp": 0, "fn": 0, "precision": 1.0, "recall": 1.0, "f1": 1.0, "missed": [], "extra": []}
    assert empty["verified_precision"] == 1.0 and empty["n_unverified"] == 0
