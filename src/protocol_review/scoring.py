"""Derived quality score (display only - it never drives the decision).

The decision (PASS / NEEDS_HUMAN_REVIEW / MAJOR_CONCERNS / RETURNED_ADMIN) is
taken from the findings by `agents.coordinator.decide`. This score summarises
the same findings as one number so protocols can be compared and trended:

    score = 100 - sum(weight[severity] for every VERIFIED finding), floored at 0

Only verified findings count. Unverified ones are reported next to the score
("pending human review"), rejected ones are ignored. When the submission was
returned at the administrative stage the scientific agents did not run, so the
score covers the administrative part plus the deterministic scientific checks
only and `scope` says so. Every deduction is listed, so each point is explainable.
"""
from __future__ import annotations

from .state import FindingStatus, Severity

WEIGHTS: dict[str, int] = {
    Severity.CRITICAL.value: 25,
    Severity.MAJOR.value: 10,
    Severity.MINOR.value: 3,
    Severity.INFO.value: 0,
}


def compute_score(findings: list[dict], admin_ok: bool = True, weights: dict[str, int] | None = None) -> dict:
    w = weights or WEIGHTS
    deductions = []
    pending = 0
    for f in findings:
        status = f.get("status")
        if status == FindingStatus.VERIFIED.value:
            pts = w.get(f.get("severity", ""), 0)
            if pts:
                deductions.append({"id": f.get("id"), "severity": f.get("severity"), "points": pts, "title": f.get("title", "")})
        elif status in (FindingStatus.UNVERIFIED.value, FindingStatus.REVISE.value, FindingStatus.PROPOSED.value):
            pending += 1
    total = sum(d["points"] for d in deductions)
    return {
        "score": max(0, 100 - total),
        "max_score": 100,
        "deducted": total,
        "deductions": deductions,
        "pending_human_review": pending,
        "scope": "full" if admin_ok else "administrative_only",
        "weights": dict(w),
    }


def score_line(score: dict | None) -> str:
    """One-line human summary for reports and emails."""
    if not score:
        return ""
    s = f"Score: {score['score']}/100"
    if score.get("deductions"):
        by = {}
        for d in score["deductions"]:
            by[d["severity"]] = by.get(d["severity"], 0) + 1
        s += " (-" + ", -".join(f"{d['points']} {d['severity']}" for d in sorted(score["deductions"], key=lambda x: -x["points"])[:6]) + ")" \
            if len(score["deductions"]) <= 6 else \
            " (" + ", ".join(f"{n} {sev}" for sev, n in by.items()) + f", -{score['deducted']} total)"
    if score.get("pending_human_review"):
        s += f"; {score['pending_human_review']} finding(s) pending human review, not counted"
    if score.get("scope") == "administrative_only":
        s += "; administrative part only - scientific agents did not run"
    return s
