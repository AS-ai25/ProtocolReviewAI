"""Rule-Based Baseline (Checkpoint 1): the deterministic checks alone, no agents.

Produces the same Finding format and decision vocabulary as the multi-agent
pipeline so `eval/evaluate.py` can compare them head-to-head.
"""
from __future__ import annotations

import json
from pathlib import Path

from .pdf_parser import parse_pdf
from .reports import run_dir
from .scoring import compute_score
from .state import Decision, FindingStatus, Severity
from .tools import checks, clinicaltrials


def run_baseline(pdf_path: str | Path, *, nct_id: str = "", registry_fetch=None, run_id: str | None = None,
                 write: bool = True) -> dict:
    parsed = parse_pdf(pdf_path)
    meta = parsed["protocol_meta"]
    nct = nct_id or meta.get("nct_id", "")
    meta["nct_id"] = nct
    registry = clinicaltrials.lookup(nct, fetch=registry_fetch).model_dump(mode="json") if nct else None
    findings = checks.all_rule_checks(parsed["pages"], meta, registry)
    for f in findings:
        f["status"] = FindingStatus.VERIFIED.value
        f["critic_notes"] = "Deterministic check."

    blocking = [f for f in findings if f["domain"] == "administrative" and f["severity"] != Severity.INFO.value]
    if blocking:
        decision = Decision.RETURNED_ADMIN
    elif any(f["severity"] in (Severity.CRITICAL.value, Severity.MAJOR.value) for f in findings):
        decision = Decision.MAJOR_CONCERNS
    else:
        decision = Decision.PASS

    result = {
        "run_id": run_id or "baseline",
        "mode": "rule_based_baseline",
        "pdf_path": str(pdf_path),
        "protocol_meta": meta,
        "registry": registry,
        "findings": findings,
        "decision": decision.value,
        "score": compute_score(findings, admin_ok=not blocking),
        "final_summary": f"Rule-based baseline: {len(findings)} findings, decision {decision.value}.",
    }
    if write:
        d = run_dir(result["run_id"])
        (d / "baseline_findings.json").write_text(json.dumps(findings, indent=1, ensure_ascii=False), encoding="utf-8")
        (d / "baseline_result.json").write_text(json.dumps(result, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
        result["paths"] = {"findings": str(d / "baseline_findings.json"), "result": str(d / "baseline_result.json")}
    return result
