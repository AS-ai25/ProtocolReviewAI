"""Reports written to outputs/<run_id>/: Markdown + PDF (charter v1.3, item 3).

Every finding row carries: id, category, severity, verification status, protocol
section, page, verbatim quote, guideline reference, explanation and required action.
Missing metadata is shown as "not found", never invented. PDFs are rendered with
xhtml2pdf (pure Python, no browser needed on the server).
"""
from __future__ import annotations

import html
import json
import logging
from datetime import datetime
from pathlib import Path

import markdown

from .config import settings
from .scoring import score_line
from .state import Domain, ReviewState

log = logging.getLogger(__name__)
SEV_ORDER = {"critical": 0, "major": 1, "minor": 2, "info": 3}
STATUS_LABEL = {"verified": "VERIFIED", "unverified": "UNVERIFIED", "revise": "REVISE", "rejected": "REJECTED",
                "proposed": "PROPOSED", "withdrawn": "WITHDRAWN"}
NF = "not found"


def run_dir(run_id: str) -> Path:
    d = settings.output_path / run_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _sorted(findings: list[dict]) -> list[dict]:
    return sorted(findings, key=lambda x: (x["status"] in ("rejected", "withdrawn"), SEV_ORDER.get(x["severity"], 9), x["id"]))


def _cell(s) -> str:
    return str(s if s not in (None, "") else "-").replace("|", "/").replace("\n", " ")


def _findings_table(findings: list[dict]) -> str:
    if not findings:
        return "_No findings._\n"
    rows = ["| ID | Severity | Status | Finding (category) | Section / page | Guideline |",
            "|---|---|---|---|---|---|"]
    for f in _sorted(findings):
        pages = ", ".join(str(e.get("page")) for e in f.get("evidence") or [] if e.get("page")) or "-"
        where = f"{_cell(f.get('section'))} / p. {pages}" if f.get("section") else f"absent / p. {pages}"
        cat = _cell(f["category"]).replace("_", " ").lower()
        rows.append(f"| {f['id']} | {f['severity']} | {STATUS_LABEL.get(f['status'], f['status'])} | "
                    f"{_cell(f['title'])} ({cat}) | {where} | {_cell(f.get('guideline_ref'))} |")
    return "\n".join(rows) + "\n"


def _findings_detail(findings: list[dict]) -> str:
    out = []
    for f in _sorted(findings):
        out.append(f"### {f['id']} - {f['title']}\n")
        out.append(f"- **Severity:** {f['severity']}  **Status:** {STATUS_LABEL.get(f['status'], f['status'])}  "
                   f"**Category:** {f['category']}  **Guideline:** {f.get('guideline_ref') or '-'}  **Source:** {f.get('source')}")
        out.append(f"- **Location:** section {f.get('section') or 'n/a (absent from the document)'}; "
                   f"page(s) {', '.join(str(e.get('page')) for e in f.get('evidence') or [] if e.get('page')) or 'n/a'}")
        for e in f.get("evidence") or []:
            if e.get("quote"):
                out.append(f"- **Quote (p. {e.get('page')}):** \"{e['quote']}\"")
        out.append(f"- **Explanation:** {f['description']}")
        out.append(f"- **Required action:** {f.get('recommendation') or 'Address the issue described above.'}")
        if f.get("critic_notes"):
            out.append(f"- **Verification notes:** {f['critic_notes']}")
        out.append("")
    return "\n".join(out)


def _header(state: ReviewState, title: str) -> str:
    meta = state.get("protocol_meta") or {}
    g = lambda k: meta.get(k) or NF  # noqa: E731
    return (f"# {title}\n\n"
            f"| Study metadata | |\n|---|---|\n"
            f"| Protocol title | {_cell(g('title'))} |\n"
            f"| Protocol number / version / date | {_cell(meta.get('protocol_number') or NF)} / {_cell(g('version'))} / {_cell(g('date'))} |\n"
            f"| Registry ID (NCT) | {_cell(g('nct_id'))} |\n"
            f"| Sponsor | {_cell(g('sponsor'))} |\n"
            f"| Principal investigator | {_cell(g('principal_investigator'))} |\n"
            f"| Phase | {_cell(g('phase'))} |\n"
            f"| Pages / sections detected | {meta.get('page_count', NF)} / {len((state.get('protocol_json') or {}).get('sections', []))} |\n"
            f"| Source / submitter | {state.get('source')} / {state.get('submitter') or NF} |\n"
            f"| Run / review date | {state.get('run_id')} / {datetime.utcnow():%Y-%m-%d %H:%M} UTC |\n\n")


def render_admin_report(state: ReviewState) -> str:
    rep = state.get("admin_report") or {}
    md = _header(state, "Administrative Review Report")
    md += f"**Administrative decision:** {'ACCEPTED for scientific review' if rep.get('accepted') else 'RETURNED - incomplete submission'}\n\n"
    md += f"**Summary:** {rep.get('summary', '')}\n\n"
    v = state.get("validation") or {}
    if v:
        md += f"**JSON validation:** {'passed' if v.get('valid') else 'FAILED'}"
        if v.get("errors"):
            md += " - " + "; ".join(v["errors"])
        if v.get("warnings"):
            md += f"  \nWarnings: {'; '.join(v['warnings'])}"
        md += "\n\n"
    if rep.get("checklist"):
        md += "## Checklist\n\n| Code | Satisfied | Note |\n|---|---|---|\n"
        for c in rep["checklist"]:
            md += f"| {c['code']} | {'yes' if c['satisfied'] else 'NO'} | {_cell(c.get('note', ''))} |\n"
        md += "\n"
    fs = [f for f in state.get("findings") or [] if f["domain"] == Domain.ADMINISTRATIVE.value] or rep.get("findings") or []
    md += "## Findings\n\n" + _findings_table(fs) + "\n## Details\n\n" + _findings_detail(fs)
    return md


def render_scientific_report(state: ReviewState) -> str:
    rep = state.get("scientific_report") or {}
    crit = state.get("critic_report") or {}
    md = _header(state, "Scientific Review Report")
    md += f"**Reviewer summary:** {rep.get('summary', '')}\n\n**Critic summary:** {crit.get('summary', '')}\n\n"
    rounds = state.get("critic_reports") or []
    if len(rounds) > 1:
        md += f"_Revision rounds: {len(rounds) - 1}. Earlier reports are kept in state.json (append-only)._\n\n"
    if rep.get("registry_comparison"):
        md += "## Protocol vs ClinicalTrials.gov\n\n| Field | Protocol | Registry | Match |\n|---|---|---|---|\n"
        for r in rep["registry_comparison"]:
            md += f"| {_cell(r['field'])} | {_cell(r['protocol_value'])} | {_cell(r['registry_value'])} | {'yes' if r['match'] else 'NO'} |\n"
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
    md += f"## Decision: **{state.get('decision')}**\n\n"
    if state.get("decision_rationale"):
        md += f"**Rule applied:** {state['decision_rationale']}  \n"
    if state.get("score"):
        th = state["score"].get("thresholds", {})
        md += (f"**{score_line(state['score'])}**  \n_Hybrid rule: any verified critical finding = MAJOR_CONCERNS; otherwise score >= {th.get('pass_min', 90)} PASS, "
               f"{th.get('human_min', 70)}-{th.get('pass_min', 90) - 1} NEEDS_HUMAN_REVIEW, below MAJOR_CONCERNS; unverified findings prevent an automatic PASS._\n\n")
    md += f"{state.get('final_summary', '')}\n\n"
    active = [f for f in fs if f["status"] not in ("rejected", "withdrawn")]
    dropped = [f for f in fs if f["status"] in ("rejected", "withdrawn")]
    md += "## Findings\n\n" + _findings_table(active) + "\n## Details\n\n" + _findings_detail(active)
    if dropped:
        md += "\n## Rejected or withdrawn findings (audit trail)\n\n" + _findings_table(dropped)
    md += "\n## Review trace\n\n| Time (UTC) | Agent | Event | Detail |\n|---|---|---|---|\n"
    for t in state.get("trace") or []:
        md += f"| {t['ts']} | {t['agent']} | {t['event']} | {_cell(t.get('detail', ''))} |\n"
    if state.get("errors"):
        md += "\n## Errors during the run\n\n" + "\n".join(f"- {e}" for e in state["errors"]) + "\n"
    md += "\n---\n_This report supports, but does not replace, professional committee review. The system grants no ethical or scientific approval._\n"
    return md


PDF_CSS = """
@page { size: A4; margin: 1.6cm; }
body { font-family: Helvetica, Arial, sans-serif; font-size: 9.5pt; color: #1b2430; }
h1 { font-size: 18pt; color: #1e3a6e; } h2 { font-size: 13pt; color: #1e3a6e; margin-top: 14pt; } h3 { font-size: 10.5pt; color: #0f6e56; }
table { width: 100%; font-size: 8.5pt; margin: 6pt 0; }
th, td { border: 0.5pt solid #9aa5b5; padding: 3pt 4pt; vertical-align: top; }
th { background-color: #eef2f7; }
code { font-family: Courier; font-size: 8.5pt; }
"""


def markdown_to_pdf(md_text: str, pdf_path: Path, title: str = "Report") -> bool:
    """Render Markdown to PDF. Returns False (and logs) on failure instead of raising."""
    try:
        from xhtml2pdf import pisa
        body = markdown.markdown(md_text, extensions=["tables"])
        doc = f"<html><head><meta charset='utf-8'><title>{html.escape(title)}</title><style>{PDF_CSS}</style></head><body>{body}</body></html>"
        with open(pdf_path, "wb") as fh:
            result = pisa.CreatePDF(doc, dest=fh, encoding="utf-8")
        if result.err:
            log.warning("xhtml2pdf reported %s error(s) for %s", result.err, pdf_path.name)
        return pdf_path.exists() and pdf_path.stat().st_size > 0
    except Exception as exc:  # never fail the run because of PDF rendering
        log.exception("PDF rendering failed for %s: %s", pdf_path.name, exc)
        return False


def write_reports(state: ReviewState) -> dict:
    d = run_dir(state["run_id"])
    paths: dict[str, str] = {}
    files = {"final_report": render_final_report(state), "administrative_report": render_admin_report(state)}
    if state.get("scientific_report") is not None:
        files["scientific_report"] = render_scientific_report(state)
    for name, content in files.items():
        md_path = d / f"{name}.md"
        md_path.write_text(content, encoding="utf-8")
        paths[name] = str(md_path)
        pdf_path = d / f"{name}.pdf"
        if markdown_to_pdf(content, pdf_path, title=name.replace("_", " ").title()):
            paths[f"{name}_pdf"] = str(pdf_path)
    (d / "findings.json").write_text(json.dumps(state.get("findings") or [], indent=1, ensure_ascii=False), encoding="utf-8")
    if state.get("protocol_json"):
        (d / "protocol.json").write_text(json.dumps(state["protocol_json"], indent=1, ensure_ascii=False), encoding="utf-8")
        paths["protocol_json"] = str(d / "protocol.json")
    slim = {k: v for k, v in state.items() if k not in ("pdf_text", "pages", "protocol_json")}
    (d / "state.json").write_text(json.dumps(slim, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    paths["findings"] = str(d / "findings.json")
    paths["state"] = str(d / "state.json")
    return paths
