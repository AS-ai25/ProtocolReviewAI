"""Administrative Review Agent (LangGraph node)."""
from __future__ import annotations

import json
import logging

from .. import memory
from ..knowledge_base import kb_text
from ..llm import LLMError
from ..state import AdminReport, Domain, FindingStatus, ReviewState, Severity, trace_event
from . import base
from .prompts import ADMIN_SYSTEM

log = logging.getLogger(__name__)
AGENT = "administrative"


def _user_prompt(state: ReviewState, rule_findings: list[dict], previous: list[dict]) -> str:
    meta = state.get("protocol_meta") or {}
    mem = memory.memories_block(AGENT, {"sponsor": meta.get("sponsor", ""), "submitter": state.get("submitter", "")})
    parts = [
        "# Administrative checklist (knowledge base)\n" + kb_text("administrative"),
        mem,
        "# Metadata extracted from the PDF\n" + json.dumps(meta, indent=1, ensure_ascii=False),
        "# Deterministic rule findings already produced (do not duplicate)\n" + base.findings_json(rule_findings),
    ]
    if state.get("admin_revise_rounds", 0) > 0:
        parts.append("# REVISION ROUND - administrative critic feedback you must address\n"
                     + "\n".join(f"- {r}" for r in state.get("admin_revise_requests") or []))
        parts.append("# Your previous findings (revise, correct or withdraw; re-emit the full list)\n" + base.findings_json(previous))
    parts += ["# Protocol text (with page markers)\n" + base.protocol_text(state), "Return the AdminReport JSON now."]
    return "\n\n".join(p for p in parts if p)


def administrative_node(state: ReviewState, llm) -> dict:
    run_id = state.get("run_id", "")
    rounds = state.get("admin_revise_rounds", 0)
    rule_findings = [f for f in state.get("rule_findings") or [] if f["domain"] == Domain.ADMINISTRATIVE.value]
    for f in rule_findings:
        f["status"] = FindingStatus.VERIFIED.value
        f["critic_notes"] = "Deterministic check (code), verified by construction."
    previous_llm = [f for f in state.get("findings") or [] if f["domain"] == Domain.ADMINISTRATIVE.value and f["source"] == "llm"]

    trace = trace_event(state, AGENT, "start", f"round={rounds}, {len(rule_findings)} rule findings")
    errors = list(state.get("errors") or [])
    report: AdminReport | None = None
    try:
        report = llm.structured(agent=AGENT, system=ADMIN_SYSTEM, user=_user_prompt(state, rule_findings, previous_llm), schema=AdminReport)
    except LLMError as exc:
        log.error("administrative agent LLM failure: %s", exc)
        errors.append(f"administrative: {exc}")
        trace = trace_event({"trace": trace}, AGENT, "llm_error", str(exc))

    # LLM findings start as PROPOSED; the Administrative Critic (next node) decides their status.
    llm_findings: list[dict] = []
    if report is not None:
        for f in base.renumber([x.model_dump(mode="json") for x in report.findings], "ADM"):
            f["domain"] = Domain.ADMINISTRATIVE.value
            f["source"] = "llm"
            f["status"] = FindingStatus.PROPOSED.value
            f["critic_notes"] = ""
            llm_findings.append(f)
    elif previous_llm:
        llm_findings = previous_llm  # keep last round's findings if the revision call failed

    admin_findings = rule_findings + llm_findings
    accepted_by_llm = report.accepted if report is not None else (state.get("admin_report") or {}).get("accepted_by_agent", True)
    # Provisional decision: only rule findings are verified at this point; the critic recomputes it.
    blocking = [f for f in admin_findings if f["severity"] == Severity.CRITICAL.value and f["status"] == FindingStatus.VERIFIED.value]
    admin_ok = accepted_by_llm and not blocking

    report_dict = {
        "accepted": admin_ok,
        "accepted_by_agent": accepted_by_llm,
        "summary": report.summary if report else "Administrative agent unavailable; decision based on deterministic checks only.",
        "checklist": [c.model_dump(mode="json") for c in report.checklist] if report else [],
        "findings": admin_findings,
        "blocking_findings": [f["id"] for f in blocking],
    }
    memory.post_message(run_id, AGENT, f"Administrative review round {rounds} done. accepted={admin_ok}. "
                        f"{len(admin_findings)} findings ({len(llm_findings)} proposed by the agent, {len(blocking)} blocking). "
                        f"{report_dict['summary'][:800]}")
    trace = trace_event({"trace": trace}, AGENT, "done", f"accepted={admin_ok}, findings={len(admin_findings)}, blocking={len(blocking)}")
    return {"admin_report": report_dict, "admin_ok": admin_ok, "findings": admin_findings, "trace": trace, "errors": errors}
