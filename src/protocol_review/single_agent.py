"""Single-Agent Baseline: ONE Claude call with everything the multi-agent system has.

The charter asks for a comparison of the multi-agent pipeline against a single
agent that receives the same tools and data. This module gives one LLM call:

* the full protocol text with page markers,
* both knowledge-base domains (administrative checklist + SPIRIT / ICH-GCP),
* the deterministic rule findings (the same `tools.checks` the agents use),
* the ClinicalTrials.gov registry summary,
* the human-approved long-term memories of every review agent.

It returns the same result shape as `baseline.run_baseline` (findings in the
`Finding` format, a decision from the shared vocabulary, a final summary) so
`eval/evaluate.py --mode single` can score it next to the rule-based baseline
and the multi-agent system. Evidence verification (`agents.base.verify_evidence`)
is applied exactly as in the multi-agent flow: a quote the code cannot locate
in the PDF is never `verified`. There is no critic and no revision round - that
is the point of the comparison.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path

from . import memory
from .agents import base
from .agents.coordinator import decide
from .agents.prompts import SINGLE_AGENT_SYSTEM
from .knowledge_base import kb_text, rule_codes
from .llm import LLMError, make_llm
from .pdf_parser import parse_pdf
from .protocol_json import build_protocol_json
from .reports import run_dir
from .scoring import compute_score
from .state import Domain, FindingStatus, Severity, SingleAgentReport
from .tools import checks, clinicaltrials

log = logging.getLogger(__name__)
AGENT = "single_agent"
MEMORY_AGENTS = ("single_agent", "administrative", "scientific_reviewer", "scientific_critic", "administrative_critic")


def _memories_block(meta: dict) -> str:
    """Approved lessons of every agent, so the single agent is not disadvantaged."""
    refs = {"sponsor": meta.get("sponsor", "")}
    seen, lines = set(), []
    for agent in MEMORY_AGENTS:
        for m in memory.recall_memories(agent, refs):
            if m["fact"] in seen:
                continue
            seen.add(m["fact"])
            tag = m["scope"] if m["scope"] == "global" else f"{m['scope']}: {m['scope_ref']}"
            lines.append(f"- [{tag}] {m['fact']}")
    if not lines:
        return ""
    return "## Approved lessons from previous reviews (human-approved long-term memory)\n" + "\n".join(lines)


def build_user_prompt(pdf_text: str, meta: dict, rule_findings: list[dict], registry: dict | None) -> str:
    return "\n\n".join(filter(None, [
        "# Administrative checklist (knowledge base)\n" + kb_text("administrative"),
        "# Scientific knowledge base (SPIRIT, ICH-GCP)\n" + kb_text("scientific"),
        _memories_block(meta),
        "# Metadata extracted from the PDF\n" + json.dumps(meta, indent=1, ensure_ascii=False),
        "# " + clinicaltrials.registry_summary(registry or {}),
        "# Deterministic rule findings already produced (do not duplicate)\n" + base.findings_json(rule_findings),
        "# Protocol text (with page markers)\n" + base.protocol_text({"pdf_text": pdf_text}),
        "Return the SingleAgentReport JSON now.",
    ]))


def apply_evidence_verification(findings: list[dict], pages: list[dict], codes: set[str]) -> list[dict]:
    """No critic exists here, so the agent's own claim stands unless the code disproves it:
    an unlocated quote or an unknown guideline code makes the finding `unverified`."""
    out = []
    for f in findings:
        v = base.verify_evidence(f, pages, codes)
        f = dict(f)
        if v["evidence_checked"] and v["evidence_found"] < v["evidence_checked"]:
            f["status"] = FindingStatus.UNVERIFIED.value
            f["critic_notes"] = "Evidence quote not located in the protocol (automatic check); human review required."
        elif not v["guideline_ref_valid"]:
            f["status"] = FindingStatus.UNVERIFIED.value
            f["critic_notes"] = "Guideline code missing or unknown (automatic check); human review required."
        else:
            f["status"] = FindingStatus.VERIFIED.value
            f["critic_notes"] = ("Single-agent claim; quote(s) located in the protocol and guideline code valid "
                                 "(automatic check, no independent critic).")
        f["evidence_check"] = v
        out.append(f)
    return out


def apply_model_status(findings: list[dict]) -> list[dict]:
    """Ablation (`verify=False`): no code check at all. The model's own claim stands: a finding it did
    not explicitly mark otherwise (unverified / rejected ...) is reported as `verified`."""
    out = []
    for f in findings:
        f = dict(f)
        if f.get("status") in (FindingStatus.PROPOSED.value, None, ""):
            f["status"] = FindingStatus.VERIFIED.value
        f["critic_notes"] = "Single-agent claim; NO code verification (ablation: --no-verification)."
        out.append(f)
    return out


def run_single_agent(pdf_path: str | Path, *, nct_id: str = "", registry_fetch=None, run_id: str | None = None,
                     llm=None, no_llm: bool | None = None, write: bool = True, verify: bool = True) -> dict:
    """One LLM call over the whole review problem. Returns the `run_baseline` result shape.

    `verify=False` is the ablation switch: the code-level evidence verification is skipped and the
    findings keep the status the model gave them (unmarked ones count as verified)."""
    run_id = run_id or datetime.utcnow().strftime("single-%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6]
    pdf_path = str(pdf_path)
    memory.create_run(run_id, "single_agent", "", pdf_path)
    if llm is None:
        llm = make_llm(on_interaction=memory.interaction_hook(run_id), no_llm=no_llm)
    elif getattr(llm, "on_interaction", None) is None:
        llm.on_interaction = memory.interaction_hook(run_id)

    parsed = parse_pdf(pdf_path)
    pages, meta = parsed["pages"], parsed["protocol_meta"]
    nct = nct_id or meta.get("nct_id", "")
    meta["nct_id"] = nct
    registry = clinicaltrials.lookup(nct, fetch=registry_fetch).model_dump(mode="json") if nct else None
    rule_findings = checks.all_rule_checks(pages, meta, registry)
    for f in rule_findings:
        f["status"] = FindingStatus.VERIFIED.value
        f["critic_notes"] = "Deterministic check (code), verified by construction."
    memory.update_run(run_id, status="running", nct_id=nct)

    errors: list[str] = []
    report: SingleAgentReport | None = None
    try:
        report = llm.structured(agent=AGENT, system=SINGLE_AGENT_SYSTEM,
                               user=build_user_prompt(parsed["pdf_text"], meta, rule_findings, registry),
                               schema=SingleAgentReport)
    except LLMError as exc:
        log.error("single agent LLM failure: %s", exc)
        errors.append(f"single_agent: {exc}")

    llm_findings: list[dict] = []
    if report is not None:
        codes = rule_codes()
        raw = [x.model_dump(mode="json") for x in report.findings]
        admin = base.renumber([f for f in raw if f["domain"] == Domain.ADMINISTRATIVE.value], "ADM")
        sci = base.renumber([f for f in raw if f["domain"] == Domain.SCIENTIFIC.value], "SCI")
        for f in admin + sci:
            f["source"] = "llm"
        llm_findings = apply_evidence_verification(admin + sci, pages, codes) if verify else apply_model_status(admin + sci)
    base.attach_sections(rule_findings + llm_findings, build_protocol_json(pages, meta, pdf_path))

    findings = rule_findings + llm_findings
    blocking = [f for f in findings if f["domain"] == Domain.ADMINISTRATIVE.value
                and f["severity"] != Severity.INFO.value and f["status"] == FindingStatus.VERIFIED.value]
    admin_ok = (report.admin_accepted if report is not None else True) and not blocking
    # Same decision rule as the coordinator -> comparable decisions across modes
    decision = decide({"admin_ok": admin_ok, "findings": findings})

    if report is not None:
        final_summary = (report.executive_summary + "\n\nKey findings:\n"
                         + "\n".join(f"- {f['id']} [{f['severity']}/{f['status']}] {f['title']}" for f in findings
                                     if f["status"] == FindingStatus.VERIFIED.value and f["severity"] in ("critical", "major"))
                         + f"\n\nRecommendation: {report.recommendation}")
    else:
        final_summary = (f"Single-agent baseline: LLM unavailable ({'; '.join(errors)}). "
                         f"{len(findings)} deterministic findings, decision {decision.value}.")

    result = {
        "run_id": run_id,
        "mode": "single_agent" if verify else "single_agent_no_verification",
        "pdf_path": pdf_path,
        "protocol_meta": meta,
        "registry": registry,
        "findings": findings,
        "admin_ok": admin_ok,
        "admin_summary": report.admin_summary if report else "",
        "scientific_summary": report.scientific_summary if report else "",
        "checklist": [c.model_dump(mode="json") for c in report.checklist] if report else [],
        "registry_comparison": [r.model_dump(mode="json") for r in report.registry_comparison] if report else [],
        "open_questions": report.open_questions if report else [],
        "decision": decision.value,
        "score": compute_score(findings, admin_ok=admin_ok),
        "final_summary": final_summary,
        "errors": errors,
        "cost": memory.run_cost_summary(run_id),
    }
    memory.post_message(run_id, AGENT, f"Single-agent review done. decision={decision.value}, "
                        f"{len(findings)} findings ({len(llm_findings)} from the LLM, {len(blocking)} blocking).")
    if write:
        d = run_dir(run_id)
        (d / "single_agent_findings.json").write_text(json.dumps(findings, indent=1, ensure_ascii=False), encoding="utf-8")
        (d / "single_agent_result.json").write_text(json.dumps(result, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
        result["paths"] = {"findings": str(d / "single_agent_findings.json"), "result": str(d / "single_agent_result.json")}
    memory.update_run(run_id, status="done", decision=decision.value, finished_at=datetime.utcnow(),
                      state={k: v for k, v in result.items() if k != "findings"} | {"n_findings": len(findings)})
    return result
