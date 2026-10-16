"""Coordinator Agent: intake, routing decisions and the final summary for the boss."""
from __future__ import annotations

import json
import logging

from .. import memory
from ..config import settings
from ..llm import LLMError
from ..pdf_parser import parse_pdf
from ..state import Decision, Domain, FinalSummary, FindingStatus, ReviewState, Severity, trace_event
from ..tools import checks
from . import base
from .prompts import COORDINATOR_SYSTEM

log = logging.getLogger(__name__)
AGENT = "coordinator"


# ------------------------------------------------------------------ intake
def intake_node(state: ReviewState) -> dict:
    run_id = state["run_id"]
    parsed = parse_pdf(state["pdf_path"])
    meta = parsed["protocol_meta"]
    nct = state.get("nct_id") or meta.get("nct_id", "")
    meta["nct_id"] = nct
    rule_findings = checks.administrative_checks(parsed["pages"], meta) + checks.scientific_checks(parsed["pages"], meta)
    memory.update_run(run_id, status="running", nct_id=nct)
    memory.post_message(run_id, AGENT, f"New protocol received from {state.get('source', 'unknown')} "
                        f"({state.get('submitter', '')}). {meta.get('page_count')} pages, NCT={nct or 'none'}. "
                        f"Forwarding to the Administrative Review Agent.", role="system")
    trace = trace_event(state, AGENT, "intake", f"pages={meta.get('page_count')} nct={nct} rule_findings={len(rule_findings)}")
    return {**parsed, "nct_id": nct, "rule_findings": rule_findings, "findings": [], "revise_rounds": 0,
            "revise_requests": [], "registry": None, "errors": [], "notifications": [], "trace": trace}


# ----------------------------------------------------------------- routing
def route_after_admin(state: ReviewState) -> str:
    return "scientific_reviewer" if state.get("admin_ok") else "finalize"


def route_after_critic(state: ReviewState) -> str:
    if state.get("revise_requests") and state.get("revise_rounds", 0) < settings.max_revise_rounds:
        return "revise"
    return "finalize"


def bump_round_node(state: ReviewState) -> dict:
    rounds = state.get("revise_rounds", 0) + 1
    memory.post_message(state["run_id"], AGENT, f"Critic requested a focused re-check (round {rounds}). "
                        f"Requests: {len(state.get('revise_requests') or [])}.")
    return {"revise_rounds": rounds, "trace": trace_event(state, AGENT, "revise_round", f"round={rounds}")}


# ---------------------------------------------------------------- decision
def decide(state: ReviewState) -> Decision:
    if not state.get("admin_ok"):
        return Decision.RETURNED_ADMIN
    fs = state.get("findings") or []
    verified = [f for f in fs if f["status"] == FindingStatus.VERIFIED.value]
    unverified = [f for f in fs if f["status"] in (FindingStatus.UNVERIFIED.value, FindingStatus.REVISE.value, FindingStatus.PROPOSED.value)]
    if any(f["severity"] in (Severity.CRITICAL.value, Severity.MAJOR.value) for f in verified):
        return Decision.MAJOR_CONCERNS
    if unverified:
        return Decision.NEEDS_HUMAN_REVIEW
    return Decision.PASS


def _deterministic_summary(state: ReviewState, decision: Decision) -> FinalSummary:
    fs = state.get("findings") or []
    counts = {s: sum(1 for f in fs if f["status"] == s) for s in ("verified", "unverified", "revise", "rejected", "proposed")}
    meta = state.get("protocol_meta") or {}
    key = [f"{f['id']} [{f['severity']}] {f['title']}" for f in fs
           if f["status"] == FindingStatus.VERIFIED.value and f["severity"] in ("critical", "major")][:8]
    key += [f"{f['id']} [UNVERIFIED] {f['title']}" for f in fs if f["status"] == FindingStatus.UNVERIFIED.value][:4]
    rec = {
        Decision.RETURNED_ADMIN: "Return the submission to the investigator with the administrative report; scientific review was not started.",
        Decision.MAJOR_CONCERNS: "Forward the report to the committee and ask the investigators to address the verified major findings before the meeting.",
        Decision.NEEDS_HUMAN_REVIEW: "A committee member should check the unverified findings before the report is circulated.",
        Decision.PASS: "Circulate the report to the committee; no blocking issues were found by the automated review.",
    }[decision]
    return FinalSummary(
        executive_summary=(f"Protocol '{meta.get('title', '')[:120]}' (NCT {meta.get('nct_id') or 'n/a'}, version {meta.get('version') or 'n/a'}) "
                           f"was reviewed. Decision: {decision.value}. Findings: {counts['verified']} verified, "
                           f"{counts['unverified'] + counts['revise'] + counts['proposed']} unverified, {counts['rejected']} rejected by the critic."),
        key_findings=key, recommendation=rec)


def finalize_node(state: ReviewState, llm) -> dict:
    run_id = state["run_id"]
    findings = [dict(f) for f in state.get("findings") or []]
    for f in findings:  # nothing may leave the system in a transient state
        if f["status"] in (FindingStatus.PROPOSED.value, FindingStatus.REVISE.value):
            f["status"] = FindingStatus.UNVERIFIED.value
            f["critic_notes"] = (f.get("critic_notes") or "") + " [left unverified at finalisation]"
    state = {**state, "findings": findings}
    decision = decide(state)
    trace = trace_event(state, AGENT, "decision", decision.value)
    errors = list(state.get("errors") or [])

    summary = None
    if llm is not None:
        try:
            payload = {
                "decision": decision.value,
                "protocol_meta": state.get("protocol_meta"),
                "admin_summary": (state.get("admin_report") or {}).get("summary"),
                "scientific_summary": (state.get("scientific_report") or {}).get("summary"),
                "critic_summary": (state.get("critic_report") or {}).get("summary"),
                "open_questions": (state.get("scientific_report") or {}).get("open_questions"),
                "errors": errors,
            }
            summary = llm.structured(
                agent=AGENT, system=COORDINATOR_SYSTEM, schema=FinalSummary,
                user="# Review outcome\n" + json.dumps(payload, indent=1, ensure_ascii=False)
                     + "\n\n# All findings\n" + base.findings_json(findings) + "\n\nReturn the FinalSummary JSON now.")
        except LLMError as exc:
            errors.append(f"coordinator: {exc}")
            trace = trace_event({"trace": trace}, AGENT, "llm_error", str(exc))
    if summary is None:
        summary = _deterministic_summary(state, decision)

    text = summary.executive_summary + "\n\nKey findings:\n" + "\n".join(f"- {k}" for k in summary.key_findings) \
        + f"\n\nRecommendation: {summary.recommendation}"
    memory.post_message(run_id, AGENT, f"Final decision {decision.value}. Sending summary and reports to the coordinator.")
    return {"findings": findings, "decision": decision.value, "final_summary": text, "trace": trace, "errors": errors}


def domain_counts(findings: list[dict]) -> dict:
    out: dict = {}
    for d in (Domain.ADMINISTRATIVE.value, Domain.SCIENTIFIC.value):
        sub = [f for f in findings if f["domain"] == d]
        out[d] = {"total": len(sub), **{s: sum(1 for f in sub if f["status"] == s) for s in ("verified", "unverified", "rejected")}}
    return out
