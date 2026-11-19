"""Coordinator Agent: intake, JSON validation, routing, decision rules and the final summary.

Authority limits (charter v1.3): the Coordinator never judges scientific validity and
never alters another agent's findings. The decision is a pure function of the findings
(`scoring.hybrid_decision`); the LLM is used only to word the executive summary.
"""
from __future__ import annotations

import json
import logging

from .. import memory
from ..config import settings
from ..llm import LLMError
from ..pdf_parser import parse_pdf
from ..protocol_json import build_protocol_json, section_for, validate_protocol_json
from ..scoring import compute_score, hybrid_decision, score_line
from ..state import Decision, Domain, Finding, FinalSummary, FindingStatus, ReviewState, Severity, trace_event
from ..tools import checks, evidence_tools, injection_scan
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
    protocol_json = build_protocol_json(parsed["pages"], meta, state["pdf_path"])
    rule_findings = (checks.administrative_checks(parsed["pages"], meta, state["pdf_path"])
                     + checks.scientific_checks(parsed["pages"], meta))
    base.attach_sections(rule_findings, protocol_json)
    memory.update_run(run_id, status="running", nct_id=nct)
    memory.post_message(run_id, AGENT, f"New protocol received from {state.get('source', 'unknown')} "
                        f"({state.get('submitter', '')}). {meta.get('page_count')} pages, "
                        f"{len(protocol_json['sections'])} sections, NCT={nct or 'none'}. Running JSON validation.", role="system")
    trace = trace_event(state, AGENT, "intake", f"pages={meta.get('page_count')} sections={len(protocol_json['sections'])} "
                                                f"nct={nct} rule_findings={len(rule_findings)}")
    out = {**parsed, "protocol_json": protocol_json, "nct_id": nct, "rule_findings": rule_findings, "findings": [],
           "revise_rounds": 0, "revise_requests": [], "registry": None, "errors": [], "notifications": [],
           "scientific_reports": [], "critic_reports": [], "trace": trace,
           "numbers_table": evidence_tools.numbers_table(parsed["pages"]),          # v1.7 context for every agent
           "study_design": evidence_tools.study_design(parsed["pages"])}
    if state.get("tool_use"):
        out["tool_use"] = True
        memory.post_message(run_id, AGENT, "TOOL USE: the scientific reviewer and the critic may call tools "
                            "(search_protocol, get_page, get_section, registry_field, kb_lookup, power_calc).", role="system")
    if state.get("force_scientific"):
        out["force_scientific"] = True
        memory.post_message(run_id, AGENT, "EVALUATION MODE: the scientific stage will run even if the administrative "
                            "gate fails (decision rule unchanged).", role="system")
    if state.get("no_critic"):
        out["no_critic"] = True
        memory.post_message(run_id, AGENT, "ABLATION MODE: the Scientific Critic is skipped; reviewer findings are "
                            "verified by code only.", role="system")
    return out


# ------------------------------------------------------- JSON validation tool
def validate_node(state: ReviewState) -> dict:
    """Deterministic JSON Validation Tool: structure, required fields, page references."""
    result = validate_protocol_json(state.get("protocol_json") or {})
    trace = trace_event(state, AGENT, "json_validation", f"valid={result['valid']} errors={len(result['errors'])} warnings={len(result['warnings'])}")
    out: dict = {"validation": result, "trace": trace}
    if not result["valid"]:
        f = Finding(id="ADM-V001", domain=Domain.ADMINISTRATIVE, category="VALIDATION_FAILED", severity=Severity.CRITICAL,
                    title="Protocol JSON failed structural validation",
                    description="; ".join(result["errors"]), guideline_ref="ADMIN-CHK-09",
                    recommendation="Submit a complete, text-based PDF of the protocol.",
                    status=FindingStatus.VERIFIED, critic_notes="JSON Validation Tool (code).", source="rule").model_dump(mode="json")
        out.update({"admin_ok": False, "findings": [f],
                    "admin_report": {"accepted": False, "accepted_by_agent": False, "summary": "Submission rejected by the JSON Validation Tool before administrative review.",
                                     "checklist": [], "findings": [f], "blocking_findings": [f["id"]]}})
        memory.post_message(state["run_id"], AGENT, "JSON validation FAILED: " + "; ".join(result["errors"]), role="system")
    else:
        memory.post_message(state["run_id"], AGENT, "JSON validation passed. Forwarding to the Administrative Review Agent.", role="system")
    return out


# ----------------------------------------------------------------- routing
def route_after_validation(state: ReviewState) -> str:
    return "administrative" if (state.get("validation") or {}).get("valid") else "finalize"


def route_after_admin(state: ReviewState) -> str:
    """Production: the scientific stage runs only when the administrative part is complete.
    Evaluation gate bypass (`force_scientific`): run it anyway so the scientific findings can be
    scored; the decision is still RETURNED_ADMIN when admin_ok is False (`hybrid_decision`)."""
    if state.get("admin_ok") or state.get("force_scientific"):
        return "scientific_reviewer"
    return "finalize"


def route_after_reviewer(state: ReviewState) -> str:
    """Ablation (`no_critic`): the reviewer's findings go straight to finalisation,
    verified by code only (quote located + guideline code valid), never by a critic."""
    return "finalize" if state.get("no_critic") else "scientific_critic"


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
    """Predefined decision rules only (hybrid rule). Kept as the single entry point for all modes."""
    return hybrid_decision(state.get("findings") or [], bool(state.get("admin_ok")))[0]


def _deterministic_summary(state: ReviewState, decision: Decision, rationale: str) -> FinalSummary:
    fs = state.get("findings") or []
    counts = {s: sum(1 for f in fs if f["status"] == s) for s in ("verified", "unverified", "revise", "rejected", "proposed", "withdrawn")}
    meta = state.get("protocol_meta") or {}
    key = [f"{f['id']} [{f['severity']}] {f['title']}" for f in fs
           if f["status"] == FindingStatus.VERIFIED.value and f["severity"] in ("critical", "major")][:8]
    key += [f"{f['id']} [UNVERIFIED] {f['title']}" for f in fs if f["status"] == FindingStatus.UNVERIFIED.value][:4]
    rec = {
        Decision.RETURNED_ADMIN: ("Return the submission to the investigator with the administrative report; the scientific findings "
                                  "are attached for information (evaluation gate bypass)." if state.get("scientific_report") else
                                  "Return the submission to the investigator with the administrative report; scientific review was not started."),
        Decision.MAJOR_CONCERNS: "Forward the report to the committee and ask the investigators to address the verified findings before the meeting.",
        Decision.NEEDS_HUMAN_REVIEW: "A committee member should check the flagged findings before the report is circulated.",
        Decision.PASS: "Circulate the report to the committee; no blocking issues were found by the automated review.",
    }[decision]
    return FinalSummary(
        executive_summary=(f"Protocol '{meta.get('title', '')[:120]}' (NCT {meta.get('nct_id') or 'n/a'}, version {meta.get('version') or 'n/a'}) "
                           f"was reviewed. Decision: {decision.value} ({rationale}). Findings: {counts['verified']} verified, "
                           f"{counts['unverified'] + counts['revise'] + counts['proposed']} unverified, {counts['rejected']} rejected, "
                           f"{counts['withdrawn']} withdrawn by the reviewer."),
        key_findings=key, recommendation=rec)


def finalize_node(state: ReviewState, llm) -> dict:
    run_id = state["run_id"]
    findings = [dict(f) for f in state.get("findings") or []]
    for f in findings:  # nothing may leave the system in a transient state (status annotation only)
        if f["status"] in (FindingStatus.PROPOSED.value, FindingStatus.REVISE.value):
            f["status"] = FindingStatus.UNVERIFIED.value
            f["critic_notes"] = (f.get("critic_notes") or "") + " [left unverified at finalisation]"
    if not state.get("admin_ok"):
        # Scientific agents did not run (unless force_scientific), but the deterministic scientific checks
        # cost nothing: include them so the submitter gets the full picture in one round trip.
        present = {f["id"] for f in findings}
        for f in state.get("rule_findings") or []:
            if f["domain"] == Domain.SCIENTIFIC.value and f["id"] not in present:
                f = dict(f)
                f["status"] = FindingStatus.VERIFIED.value
                f["critic_notes"] = "Deterministic check (code); scientific agents did not run because the submission was returned at the administrative stage."
                findings.append(f)
    pj = state.get("protocol_json") or {}
    for f in findings:
        if not f.get("section"):
            f["section"] = section_for(pj, next((e.get("page") for e in f.get("evidence") or [] if e.get("page")), None),
                                       next((e.get("quote") for e in f.get("evidence") or [] if e.get("quote")), ""))

    admin_ok = bool(state.get("admin_ok"))
    decision, rationale = hybrid_decision(findings, admin_ok)
    score = compute_score(findings, admin_ok=admin_ok, scientific_ran=state.get("scientific_report") is not None)
    errors = list(state.get("errors") or [])
    # M1 (mentor, 8 Nov 2026): a run in which an LLM agent did not run can never end in PASS, and must say so
    agent_failures = sorted({e.split(":")[0].strip() for e in errors
                             if e.split(":")[0].strip() in ("administrative", "scientific_reviewer", "scientific_critic")})
    if (state.get("admin_report") or {}).get("agent_failed") and "administrative" not in agent_failures:
        agent_failures.append("administrative")
    if agent_failures and decision == Decision.PASS:
        decision = Decision.NEEDS_HUMAN_REVIEW
        rationale = f"agent(s) did not run ({', '.join(agent_failures)}); automated PASS not allowed"
    elif agent_failures:
        rationale += f"; agent(s) did not run: {', '.join(agent_failures)}"
    # Intake scan (19 Nov 2026): a protocol with text that addresses an automated reviewer never ends in PASS either
    decision, rationale, suspect_ids = injection_scan.apply_cap(findings + list(state.get("rule_findings") or []), decision, rationale)
    trace = trace_event(state, AGENT, "decision", f"{decision.value} [{rationale}]; {score_line(score)}")

    summary = None
    if llm is not None:
        try:
            payload = {
                "decision": decision.value,
                "decision_rationale": rationale,
                "score": score_line(score),
                "protocol_meta": state.get("protocol_meta"),
                "validation": state.get("validation"),
                "admin_summary": (state.get("admin_report") or {}).get("summary"),
                "scientific_summary": (state.get("scientific_report") or {}).get("summary"),
                "critic_summary": (state.get("critic_report") or {}).get("summary"),
                "open_questions": (state.get("scientific_report") or {}).get("open_questions"),
                "errors": errors,
                "agents_that_did_not_run": agent_failures,
            }
            summary = llm.structured(
                agent=AGENT, system=COORDINATOR_SYSTEM, schema=FinalSummary,
                user="# Review outcome (decided by code - do not change it)\n" + json.dumps(payload, indent=1, ensure_ascii=False)
                     + "\n\n# All findings\n" + base.findings_json(findings) + "\n\nReturn the FinalSummary JSON now.")
        except LLMError as exc:
            errors.append(f"coordinator: {exc}")
            trace = trace_event({"trace": trace, "run_id": state.get("run_id")}, AGENT, "llm_error", str(exc))
    if summary is None:
        summary = _deterministic_summary(state, decision, rationale)

    text = summary.executive_summary + "\n\nKey findings:\n" + "\n".join(f"- {k}" for k in summary.key_findings) \
        + f"\n\nRecommendation: {summary.recommendation}"
    if agent_failures:
        text = (f"WARNING: the following agent(s) did not run (LLM error): {', '.join(agent_failures)}. Their part of the review "
                f"is missing; the findings below are incomplete and the decision is capped at NEEDS_HUMAN_REVIEW.\n\n") + text
    if suspect_ids:
        text = injection_scan.WARNING.format(ids=", ".join(suspect_ids)) + text
    memory.post_message(run_id, AGENT, f"Final decision {decision.value} ({rationale}). Sending summary and reports to the coordinator.")
    return {"findings": findings, "decision": decision.value, "decision_rationale": rationale, "score": score,
            "final_summary": text, "trace": trace, "errors": errors, "agent_failures": agent_failures}


def domain_counts(findings: list[dict]) -> dict:
    out: dict = {}
    for d in (Domain.ADMINISTRATIVE.value, Domain.SCIENTIFIC.value):
        sub = [f for f in findings if f["domain"] == d]
        out[d] = {"total": len(sub), **{s: sum(1 for f in sub if f["status"] == s) for s in ("verified", "unverified", "rejected", "withdrawn")}}
    return out
