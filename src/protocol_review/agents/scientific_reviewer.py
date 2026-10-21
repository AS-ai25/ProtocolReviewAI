"""Scientific Review Agent (LangGraph node)."""
from __future__ import annotations

import json
import logging

from .. import memory
from ..knowledge_base import kb_text, rule_codes
from ..llm import LLMError
from ..state import Domain, FindingStatus, ReviewState, ScientificReport, trace_event
from ..tools import checks, clinicaltrials
from . import base
from .prompts import SCIENTIFIC_REVIEW_SYSTEM

log = logging.getLogger(__name__)
AGENT = "scientific_reviewer"


def _user_prompt(state: ReviewState, rule_findings: list[dict], previous: list[dict]) -> str:
    meta = state.get("protocol_meta") or {}
    mem = memory.memories_block(AGENT, {"sponsor": meta.get("sponsor", "")})
    parts = [
        "# Scientific knowledge base (SPIRIT, ICH-GCP)\n" + kb_text("scientific"),
        mem,
        "# Protocol metadata\n" + json.dumps(meta, indent=1, ensure_ascii=False),
        "# " + clinicaltrials.registry_summary(state.get("registry") or {}),
        base.sections_block(state),
        "# Deterministic rule findings already produced (do not duplicate)\n" + base.findings_json(rule_findings),
    ]
    if state.get("revise_rounds", 0) > 0:
        parts.append("# REVISION ROUND - critic feedback you must address\n" + "\n".join(f"- {r}" for r in state.get("revise_requests") or []))
        parts.append("# Your previous findings (revise, correct or withdraw; re-emit the full list)\n" + base.findings_json(previous))
    parts += ["# Protocol text (with page markers)\n" + base.protocol_text(state), "Return the ScientificReport JSON now."]
    return "\n\n".join(p for p in parts if p)


def scientific_reviewer_node(state: ReviewState, llm, registry_fetch=None) -> dict:
    run_id = state.get("run_id", "")
    pages = state.get("pages") or []
    meta = state.get("protocol_meta") or {}
    trace = trace_event(state, AGENT, "start", f"round={state.get('revise_rounds', 0)}")
    errors = list(state.get("errors") or [])

    registry = state.get("registry")
    if registry is None:
        nct = state.get("nct_id") or meta.get("nct_id", "")
        registry = clinicaltrials.lookup(nct, fetch=registry_fetch).model_dump(mode="json")
        trace = trace_event({"trace": trace}, AGENT, "registry_lookup", f"{nct}: found={registry.get('found')} {registry.get('error', '')}")

    rule_sci = [f for f in state.get("rule_findings") or [] if f["domain"] == Domain.SCIENTIFIC.value]
    rule_sci += checks.registry_checks(pages, meta, registry)
    for f in rule_sci:
        f["status"] = FindingStatus.VERIFIED.value
        f["critic_notes"] = "Deterministic check (code), verified by construction."

    previous_llm = [f for f in state.get("findings") or [] if f["domain"] == Domain.SCIENTIFIC.value and f["source"] == "llm"
                    and f["status"] != FindingStatus.WITHDRAWN.value]
    already_withdrawn = [f for f in state.get("findings") or [] if f["status"] == FindingStatus.WITHDRAWN.value]
    report: ScientificReport | None = None
    try:
        report = llm.structured(agent=AGENT, system=SCIENTIFIC_REVIEW_SYSTEM,
                                user=_user_prompt({**state, "registry": registry}, rule_sci, previous_llm), schema=ScientificReport)
    except LLMError as exc:
        log.error("scientific reviewer LLM failure: %s", exc)
        errors.append(f"scientific_reviewer: {exc}")
        trace = trace_event({"trace": trace}, AGENT, "llm_error", str(exc))

    llm_findings: list[dict] = []
    if report is not None:
        for f in base.renumber([x.model_dump(mode="json") for x in report.findings], "SCI", previous=previous_llm):
            f["domain"] = Domain.SCIENTIFIC.value
            f["source"] = "llm"
            f["status"] = FindingStatus.PROPOSED.value
            f["critic_notes"] = ""
            llm_findings.append(f)
    elif previous_llm:
        llm_findings = previous_llm  # keep last round's findings if the revision call failed
    if state.get("no_critic") and llm_findings:
        # Ablation: no critic will audit these, so the status comes from the code-only evidence check
        # (exactly the single agent's rule: unlocated quote or unknown guideline code -> unverified).
        from ..single_agent import apply_evidence_verification
        llm_findings = apply_evidence_verification(llm_findings, pages, rule_codes())
        n_ok = sum(1 for f in llm_findings if f["status"] == FindingStatus.VERIFIED.value)
        trace = trace_event({"trace": trace}, AGENT, "code_only_verification", f"no_critic: {n_ok}/{len(llm_findings)} verified by code")

    admin_findings = [f for f in state.get("findings") or [] if f["domain"] == Domain.ADMINISTRATIVE.value]
    withdrawn = already_withdrawn + (base.withdraw_missing(previous_llm, llm_findings) if report is not None else [])
    sci_findings = base.attach_sections(rule_sci + llm_findings, state.get("protocol_json") or {}) + withdrawn
    report_dict = {
        "round": state.get("revise_rounds", 0),
        "summary": report.summary if report else "Scientific reviewer unavailable; deterministic checks only.",
        "registry_comparison": [r.model_dump(mode="json") for r in report.registry_comparison] if report else [],
        "open_questions": report.open_questions if report else [],
        "findings": sci_findings,
    }
    memory.post_message(run_id, AGENT, f"Scientific review round {state.get('revise_rounds', 0)} done: "
                        f"{len(sci_findings)} findings. {report_dict['summary'][:800]}")
    trace = trace_event({"trace": trace}, AGENT, "done", f"findings={len(sci_findings)} (llm={len(llm_findings)})")
    return {"registry": registry, "scientific_report": report_dict,
            "scientific_reports": list(state.get("scientific_reports") or []) + [report_dict],
            "findings": admin_findings + sci_findings, "trace": trace, "errors": errors}
