"""Markdown reports written to outputs/<run_id>/."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .config import settings
from .state import Domain, ReviewState

STATUS_ICON = {"verified": "VERIFIED", "unverified": "UNVERIFIED", "revise": "REVISE", "rejected": "REJECTED", "proposed": "PROPOSED"}


def run_dir(run_id: str) -> Path:
    d = settings.output_path / run_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _findings_table(findings: list[dict]) -> str:
    if not findings:
        return "_No findings._\n"
    rows = ["| ID | Severity | Status | Category | Title | Guideline | Evidence (page) |", "|---|---|---|---|---|---|---|"]
    for f in sorted(findings, key=lambda x: ({"critical": 0, "major": 1, "minor": 2, "info": 3}[x["severity"]], x["id"])):
        pages = ", ".join(str(e.get("page")) for e in f.get("evidence") or [] if e.get("page")) or "-"
        rows.append(f"| {f['id']} | {f['severity']} | {STATUS_ICON.get(f['status'], f['status'])} | {f['category']} | "
                    f"{f['title'].replace('|', '/')} | {f.get('guideline_ref') or '-'} | {pages} |")
    return "\n".join(rows) + "\n"


def _findings_detail(findings: list[dict]) -> str:
    out = []
    for f in findings:
        out.append(f"### {f['id']} - {f['title']}\n")
        out.append(f"- **Severity:** {f['severity']}  **Status:** {STATUS_ICON.get(f['status'], f['status'])}  "
                   f"**Category:** {f['category']}  **Guideline:** {f.get('guideline_ref') or '-'}  **Source:** {f.get('source')}")
        out.append(f"- **Description:** {f['description']}")
        if f.get("recommendation"):
            out.append(f"- **Recommendation:** {f['recommendation']}")
        for e in f.get("evidence") or []:
            if e.get("quote"):
                out.append(f"- **Evidence (p. {e.get('page')}):** \"{e['quote']}\"")
        if f.get("critic_notes"):
            out.append(f"- **Critic / verification notes:** {f['critic_notes']}")
        out.append("")
    return "\n".join(out)


def _header(state: ReviewState, title: str) -> str:
    meta = state.get("protocol_meta") or {}
    return (f"# {title}\n\n"
            f"- **Run:** {state.get('run_id')}  \n- **Generated:** {datetime.utcnow():%Y-%m-%d %H:%M} UTC  \n"
            f"- **Protocol:** {meta.get('title', '')}  \n- **Version / date:** {meta.get('version') or 'n/a'} / {meta.get('date') or 'n/a'}  \n"
            f"- **Registry ID:** {meta.get('nct_id') or 'none'}  \n- **Sponsor / PI:** {meta.get('sponsor') or 'n/a'} / {meta.get('principal_investigator') or 'n/a'}  \n"
            f"- **Source:** {state.get('source')} ({state.get('submitter') or 'unknown submitter'})  \n- **Pages:** {meta.get('page_count')}\n\n")


def render_admin_report(state: ReviewState) -> str:
    rep = state.get("admin_report") or {}
    md = _header(state, "Administrative Review Report")
    md += f"**Administrative decision:** {'ACCEPTED for scientific review' if rep.get('accepted') else 'RETURNED - incomplete submission'}\n\n"
    md += f"**Summary:** {rep.get('summary', '')}\n\n"
    crit = state.get("admin_critic_report") or {}
    if crit.get("summary"):
        md += f"**Administrative critic:** {crit['summary']}\n\n"
    if rep.get("checklist"):
        md += "## Checklist\n\n| Code | Satisfied | Note |\n|---|---|---|\n"
        for c in rep["checklist"]:
            md += f"| {c['code']} | {'yes' if c['satisfied'] else 'NO'} | {c.get('note', '')} |\n"
        md += "\n"
    fs = rep.get("findings") or []
    md += "## Findings (after critic)\n\n" + _findings_table(fs) + "\n## Details\n\n" + _findings_detail(fs)
    if crit.get("missed_issues"):
        md += "## Issues raised by the administrative critic\n\n" + "\n".join(f"- {m}" for m in crit["missed_issues"]) + "\n"
    return md


def render_scientific_report(state: ReviewState) -> str:
    rep = state.get("scientific_report") or {}
    crit = state.get("critic_report") or {}
    md = _header(state, "Scientific Review Report")
    md += f"**Reviewer summary:** {rep.get('summary', '')}\n\n**Critic summary:** {crit.get('summary', '')}\n\n"
    if rep.get("registry_comparison"):
        md += "## Protocol vs ClinicalTrials.gov\n\n| Field | Protocol | Registry | Match |\n|---|---|---|---|\n"
        for r in rep["registry_comparison"]:
            md += f"| {r['field']} | {r['protocol_value']} | {r['registry_value']} | {'yes' if r['match'] else 'NO'} |\n"
        md += "\n"
    fs = [f for f in state.get("findings") or [] if f["domain"] == Domain.SCIENTIFIC.value]
    md += "## Findings (after critic)\n\n" + _findings_table(fs) + "\n## Details\n\n" + _findings_detail(fs)
    if rep.get("open_questions"):
        md += "## Open questions for the investigators\n\n" + "\n".join(f"- {q}" for q in rep["open_questions"]) + "\n\n"
    if crit.get("missed_issues"):
        md += "## Issues raised by the critic\n\n" + "\n".join(f"- {m}" for m in crit["missed_issues"]) + "\n"
    return md


def render_final_report(state: ReviewState) -> str:
    fs = state.get("findings") or []
    md = _header(state, "Protocol Review - Final Report")
    md += f"## Decision: **{state.get('decision')}**\n\n{state.get('final_summary', '')}\n\n"
    md += "## All findings\n\n" + _findings_table(fs)
    md += "\n## Review trace\n\n| Time (UTC) | Agent | Event | Detail |\n|---|---|---|---|\n"
    for t in state.get("trace") or []:
        md += f"| {t['ts']} | {t['agent']} | {t['event']} | {t.get('detail', '').replace('|', '/')} |\n"
    if state.get("errors"):
        md += "\n## Errors during the run\n\n" + "\n".join(f"- {e}" for e in state["errors"]) + "\n"
    md += "\n---\n_This report supports, but does not replace, professional committee review._\n"
    return md


def write_reports(state: ReviewState) -> dict:
    d = run_dir(state["run_id"])
    paths = {}
    files = {"final_report.md": render_final_report(state), "administrative_report.md": render_admin_report(state)}
    if state.get("scientific_report") is not None:
        files["scientific_report.md"] = render_scientific_report(state)
    for name, content in files.items():
        (d / name).write_text(content, encoding="utf-8")
        paths[name.split(".")[0]] = str(d / name)
    (d / "findings.json").write_text(json.dumps(state.get("findings") or [], indent=1, ensure_ascii=False), encoding="utf-8")
    slim = {k: v for k, v in state.items() if k not in ("pdf_text", "pages")}
    (d / "state.json").write_text(json.dumps(slim, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    paths["findings"] = str(d / "findings.json")
    paths["state"] = str(d / "state.json")
    return paths
