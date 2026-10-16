"""Scientific Critic Agent (LangGraph node)."""
from __future__ import annotations

import json
import logging

from .. import memory
from ..config import settings
from ..knowledge_base import kb_text, rule_codes
from ..llm import LLMError
from ..state import CriticReport, Domain, Finding, FindingStatus, ReviewState, Severity, trace_event
from ..tools import clinicaltrials
from . import base
from .prompts import SCIENTIFIC_CRITIC_SYSTEM

log = logging.getLogger(__name__)
AGENT = "scientific_critic"


def _user_prompt(state: ReviewState, targets: list[dict], verifications: list[dict]) -> str:
    rep = state.get("scientific_report") or {}
    mem = memory.memories_block(AGENT)
    return "\n\n".join(filter(None, [
        "# Scientific knowledge base (SPIRIT, ICH-GCP)\n" + kb_text("scientific"),
        mem,
        "# " + clinicaltrials.registry_summary(state.get("registry") or {}),
        "# Reviewer summary\n" + (rep.get("summary") or ""),
        "# Findings to audit (return one verdict per id)\n" + base.findings_json(targets),
        "# Deterministic evidence check per finding (quotes located in the PDF? guideline code valid?)\n"
        + json.dumps(verifications, indent=1),
        "# Protocol text (with page markers)\n" + base.protocol_text(state),
        "Return the CriticReport JSON now.",
    ]))


def scientific_critic_node(state: ReviewState, llm) -> dict:
    run_id = state.get("run_id", "")
    pages = state.get("pages") or []
    findings = [dict(f) for f in state.get("findings") or []]
    targets = [f for f in findings if f["domain"] == Domain.SCIENTIFIC.value and f["source"] == "llm"
               and f["status"] in (FindingStatus.PROPOSED.value, FindingStatus.REVISE.value)]
    codes = rule_codes()
    verifications = [base.verify_evidence(f, pages, codes) for f in targets]
    trace = trace_event(state, AGENT, "start", f"{len(targets)} findings to audit")
    errors = list(state.get("errors") or [])
    rounds = state.get("revise_rounds", 0)
    last_round = rounds >= settings.max_revise_rounds

    report: CriticReport | None = None
    if targets:
        try:
            report = llm.structured(agent=AGENT, system=SCIENTIFIC_CRITIC_SYSTEM,
                                    user=_user_prompt(state, targets, verifications), schema=CriticReport)
        except LLMError as exc:
            log.error("scientific critic LLM failure: %s", exc)
            errors.append(f"scientific_critic: {exc}")
            trace = trace_event({"trace": trace}, AGENT, "llm_error", str(exc))

    verdicts = {v.finding_id: v for v in (report.verdicts if report else [])}
    by_id = {v["finding_id"]: v for v in verifications}
    revise_requests: list[str] = []
    for f in findings:
        if f not in targets:
            continue
        v = verdicts.get(f["id"])
        ver = by_id.get(f["id"], {})
        if v is None:
            f["status"] = FindingStatus.UNVERIFIED.value
            f["critic_notes"] = "No critic verdict received - human review required."
            continue
        if v.revised_severity:
            f["severity"] = v.revised_severity.value
        if v.verdict == "verified":
            # Guardrail: a quote the code could not find in the PDF is never 'verified'
            if ver.get("evidence_checked") and ver.get("evidence_found", 0) < ver.get("evidence_checked", 0):
                f["status"] = FindingStatus.UNVERIFIED.value
                f["critic_notes"] = "Critic accepted it but the quoted evidence was not located in the PDF. " + v.notes
            else:
                f["status"] = FindingStatus.VERIFIED.value
                f["critic_notes"] = v.notes
        elif v.verdict == "revise":
            if last_round:
                f["status"] = FindingStatus.UNVERIFIED.value
                f["critic_notes"] = "Revision requested but no rounds left: " + v.notes
            else:
                f["status"] = FindingStatus.REVISE.value
                f["critic_notes"] = v.notes
                revise_requests.append(f"{f['id']}: {v.notes}")
        elif v.verdict == "rejected":
            f["status"] = FindingStatus.REJECTED.value
            f["critic_notes"] = v.notes
        else:
            f["status"] = FindingStatus.UNVERIFIED.value
            f["critic_notes"] = v.notes

    missed = report.missed_issues if report else []
    if missed and not last_round:
        revise_requests += [f"MISSED: {m}" for m in missed]
    elif missed:
        n = sum(1 for f in findings if f["id"].startswith("SCI-C"))
        for m in missed:
            n += 1
            findings.append(Finding(id=f"SCI-C{n:03d}", domain=Domain.SCIENTIFIC, category="OTHER", severity=Severity.MAJOR,
                                    title="Issue raised by the critic", description=m, guideline_ref="",
                                    status=FindingStatus.UNVERIFIED, critic_notes="Raised by the critic after the last revision round; needs a human.",
                                    source="llm").model_dump(mode="json"))

    proposed_ids = []
    for fact in (report.proposed_memory if report else [])[:3]:
        mid = memory.propose_memory(AGENT, fact, scope="global", run_id=run_id, proposed_by=AGENT)
        if mid:
            proposed_ids.append(mid)

    critic_dict = {
        "summary": report.summary if report else ("No LLM findings to audit." if not targets else "Critic unavailable."),
        "verdicts": [v.model_dump(mode="json") for v in (report.verdicts if report else [])],
        "missed_issues": missed,
        "proposed_memory_ids": proposed_ids,
        "evidence_checks": verifications,
    }
    memory.post_message(run_id, AGENT, f"Critic round {rounds}: {len(verdicts)} verdicts, "
                        f"{len(revise_requests)} revision requests. {critic_dict['summary'][:800]}")
    trace = trace_event({"trace": trace}, AGENT, "done",
                        f"verdicts={len(verdicts)} revise={len(revise_requests)} missed={len(missed)} memories_proposed={len(proposed_ids)}")
    return {"critic_report": critic_dict, "findings": findings, "revise_requests": revise_requests,
            "trace": trace, "errors": errors}
