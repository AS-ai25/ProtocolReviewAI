"""Administrative Review Agent (LangGraph node)."""
from __future__ import annotations

import json
import logging

from .. import memory
from ..knowledge_base import kb_text, rule_codes
from ..llm import LLMError
from ..state import AdminReport, Domain, FindingStatus, ReviewState, Severity, trace_event
from . import base
from .prompts import ADMIN_SYSTEM

log = logging.getLogger(__name__)
AGENT = "administrative"


def _user_prompt(state: ReviewState, rule_findings: list[dict]) -> str:
    meta = state.get("protocol_meta") or {}
    mem = memory.memories_block(AGENT, {"sponsor": meta.get("sponsor", ""), "submitter": state.get("submitter", "")})
    return "\n\n".join(filter(None, [
        "# Administrative checklist (knowledge base)\n" + kb_text("administrative"),
        mem,
        "# Metadata extracted from the PDF\n" + json.dumps(meta, indent=1, ensure_ascii=False),
        base.sections_block(state),
        base.context_block(state),
        "# Deterministic rule findings already produced (do not duplicate)\n" + base.findings_json(rule_findings),
        "# Protocol text (with page markers)\n" + base.protocol_text(state),
        "Return the AdminReport JSON now.",
    ]))


def administrative_node(state: ReviewState, llm) -> dict:
    run_id = state.get("run_id", "")
    pages = state.get("pages") or []
    rule_findings = [f for f in state.get("rule_findings") or [] if f["domain"] == Domain.ADMINISTRATIVE.value]
    for f in rule_findings:
        f["status"] = FindingStatus.VERIFIED.value
        f["critic_notes"] = "Deterministic check (code), verified by construction."

    trace = trace_event(state, AGENT, "start", f"{len(rule_findings)} rule findings")
    errors = list(state.get("errors") or [])
    report: AdminReport | None = None
    try:
        report = llm.structured(agent=AGENT, system=ADMIN_SYSTEM, user=_user_prompt(state, rule_findings), schema=AdminReport)
    except LLMError as exc:
        log.error("administrative agent LLM failure: %s", exc)
        errors.append(f"administrative: {exc}")
        trace = trace_event({"trace": trace, "run_id": state.get("run_id")}, AGENT, "llm_error", str(exc))

    llm_findings: list[dict] = []
    if report is not None:
        codes = rule_codes()
        for f in base.renumber([x.model_dump(mode="json") for x in report.findings], "ADM"):
            f["domain"] = Domain.ADMINISTRATIVE.value
            f["source"] = "llm"
            v = base.verify_evidence(f, pages, codes)
            auto = base.auto_status_from_verification(v)
            floor, note = base.code_status(v)
            if auto:
                f["status"] = auto.value
                f["critic_notes"] = "Evidence quote(s) located in the protocol and guideline code valid (automatic check)."
            elif floor is not None:
                f["status"] = floor.value
                f["critic_notes"] = note
            elif v["absence_claim"] and v["guideline_ref_valid"]:
                f["status"] = FindingStatus.UNVERIFIED.value
                f["critic_notes"] = "Absence claim with valid guideline code - confirm by hand."
            else:
                f["status"] = FindingStatus.UNVERIFIED.value
                f["critic_notes"] = "Evidence quote not located in the protocol or guideline code invalid."
            f["evidence_check"] = v
            llm_findings.append(f)

    admin_findings = base.attach_sections(rule_findings + llm_findings, state.get("protocol_json") or {})
    # Policy (Amir, 2026-10-16): the administrative part must be 100% complete. ANY verified
    # administrative finding (critical, major or minor) returns the submission; "info" does not.
    blocking = [f for f in admin_findings if f["severity"] != Severity.INFO.value
                and f["status"] == FindingStatus.VERIFIED.value]
    accepted_by_llm = report.accepted if report is not None else True
    admin_ok = accepted_by_llm and not blocking

    report_dict = {
        "accepted": admin_ok,
        "accepted_by_agent": accepted_by_llm,
        "agent_failed": report is None,          # M1: the coordinator never lets such a run end in PASS
        "summary": report.summary if report else "Administrative agent unavailable; decision based on deterministic checks only.",
        "checklist": [c.model_dump(mode="json") for c in report.checklist] if report else [],
        "findings": admin_findings,
        "blocking_findings": [f["id"] for f in blocking],
    }
    memory.post_message(run_id, AGENT, f"Administrative review done. accepted={admin_ok}. "
                        f"{len(admin_findings)} findings ({len(blocking)} blocking). {report_dict['summary'][:800]}")
    trace = trace_event({"trace": trace, "run_id": state.get("run_id")}, AGENT, "done", f"accepted={admin_ok}, findings={len(admin_findings)}, blocking={len(blocking)}")
    return {"admin_report": report_dict, "admin_ok": admin_ok, "findings": admin_findings, "trace": trace, "errors": errors}
