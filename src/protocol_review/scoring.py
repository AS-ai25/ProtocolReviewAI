"""Derived quality score and the hybrid scientific decision rule (charter v1.3).

    score = 100 - sum(weight[severity] for every VERIFIED finding), floored at 0

Only verified findings count. Unverified ones are reported next to the score
("pending human review"); rejected and withdrawn ones are ignored. When the
submission was returned at the administrative stage the scientific agents did
not run, so the score covers the administrative part plus the deterministic
scientific checks only and `scope` says so. Every deduction is listed by
finding id, so each point is explainable.

Hybrid rule (team decision, 2026-10-19): any verified CRITICAL finding ->
MAJOR_CONCERNS regardless of score; otherwise score >= SCORE_PASS_MIN -> PASS,
SCORE_HUMAN_MIN..SCORE_PASS_MIN-1 -> NEEDS_HUMAN_REVIEW, below -> MAJOR_CONCERNS.
Unverified findings prevent an automatic PASS. MAJOR_CONCERNS takes precedence.
"""
from __future__ import annotations

from .config import settings
from .state import Decision, FindingStatus, Severity

WEIGHTS: dict[str, int] = {
    Severity.CRITICAL.value: 25,
    Severity.MAJOR.value: 10,
    Severity.MINOR.value: 3,
    Severity.INFO.value: 0,
}
PENDING_STATUSES = (FindingStatus.UNVERIFIED.value, FindingStatus.REVISE.value, FindingStatus.PROPOSED.value)


def compute_score(findings: list[dict], admin_ok: bool = True, weights: dict[str, int] | None = None,
                  scientific_ran: bool | None = None) -> dict:
    """`scientific_ran` overrides the scope label: with the evaluation gate bypass the scientific
    agents run although admin_ok is False, so the score then covers both parts."""
    w = weights or WEIGHTS
    if scientific_ran is None:
        scientific_ran = admin_ok
    deductions = []
    pending = 0
    for f in findings:
        status = f.get("status")
        if status == FindingStatus.VERIFIED.value:
            pts = w.get(f.get("severity", ""), 0)
            if pts:
                deductions.append({"id": f.get("id"), "severity": f.get("severity"), "points": pts, "title": f.get("title", "")})
        elif status in PENDING_STATUSES:
            pending += 1
    total = sum(d["points"] for d in deductions)
    return {
        "score": max(0, 100 - total),
        "max_score": 100,
        "deducted": total,
        "deductions": deductions,
        "pending_human_review": pending,
        "scope": "full" if admin_ok else ("full_forced" if scientific_ran else "administrative_only"),
        "weights": dict(w),
        "thresholds": {"pass_min": settings.score_pass_min, "human_min": settings.score_human_min},
    }


def hybrid_decision(findings: list[dict], admin_ok: bool) -> tuple[Decision, str]:
    """Returns (decision, rationale). Pure function of the findings - no LLM involved."""
    if not admin_ok:
        return Decision.RETURNED_ADMIN, "administrative part not 100% complete"
    verified = [f for f in findings if f.get("status") == FindingStatus.VERIFIED.value]
    pending = [f for f in findings if f.get("status") in PENDING_STATUSES]
    crit = [f["id"] for f in verified if f.get("severity") == Severity.CRITICAL.value]
    if crit:
        return Decision.MAJOR_CONCERNS, f"verified critical finding(s): {', '.join(crit)}"
    score = compute_score(findings, admin_ok=True)["score"]
    pass_min, human_min = settings.score_pass_min, settings.score_human_min
    if score < human_min:
        return Decision.MAJOR_CONCERNS, f"score {score} < {human_min}"
    if score < pass_min:
        return Decision.NEEDS_HUMAN_REVIEW, f"score {score} in {human_min}-{pass_min - 1}"
    if pending:
        return Decision.NEEDS_HUMAN_REVIEW, f"score {score} >= {pass_min} but {len(pending)} finding(s) unverified"
    return Decision.PASS, f"score {score} >= {pass_min}, no verified critical finding, nothing unverified"


def score_line(score: dict | None) -> str:
    """One-line human summary for reports and emails."""
    if not score:
        return ""
    s = f"Score: {score['score']}/100"
    if score.get("deductions"):
        by: dict[str, int] = {}
        for d in score["deductions"]:
            by[d["severity"]] = by.get(d["severity"], 0) + 1
        if len(score["deductions"]) <= 6:
            s += " (-" + ", -".join(f"{d['points']} {d['severity']}" for d in sorted(score["deductions"], key=lambda x: -x["points"])) + ")"
        else:
            s += " (" + ", ".join(f"{n} {sev}" for sev, n in by.items()) + f", -{score['deducted']} total)"
    if score.get("pending_human_review"):
        s += f"; {score['pending_human_review']} finding(s) pending human review, not counted"
    if score.get("scope") == "administrative_only":
        s += "; administrative part only - scientific agents did not run"
    elif score.get("scope") == "full_forced":
        s += "; scientific stage forced for evaluation although the administrative gate failed"
    return s
