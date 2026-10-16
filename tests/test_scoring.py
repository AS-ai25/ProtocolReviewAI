from protocol_review.scoring import compute_score, score_line


def _f(i, sev, status):
    return {"id": f"X-{i}", "severity": sev, "status": status, "title": f"t{i}"}


def test_score_counts_only_verified_findings():
    fs = [_f(1, "critical", "verified"), _f(2, "major", "verified"), _f(3, "minor", "verified"),
          _f(4, "major", "unverified"), _f(5, "critical", "rejected"), _f(6, "info", "verified")]
    s = compute_score(fs)
    assert s["score"] == 100 - 25 - 10 - 3
    assert [d["id"] for d in s["deductions"]] == ["X-1", "X-2", "X-3"]
    assert s["pending_human_review"] == 1
    assert s["scope"] == "full"
    line = score_line(s)
    assert line.startswith("Score: 62/100") and "1 finding(s) pending" in line


def test_score_floors_at_zero_and_marks_admin_scope():
    fs = [_f(i, "critical", "verified") for i in range(6)]
    s = compute_score(fs, admin_ok=False)
    assert s["score"] == 0 and s["deducted"] == 150
    assert "administrative part only" in score_line(s)
    assert compute_score([])["score"] == 100 and score_line(compute_score([])) == "Score: 100/100"
