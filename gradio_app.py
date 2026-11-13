"""End-user Gradio frontend for the existing Clinical Protocol Review FastAPI service.

No changes to the agent graph, pipeline, evaluation data or database schema.
Launch FastAPI first on http://127.0.0.1:8040, then run this file.
"""
from __future__ import annotations

import html as html_lib
import os
import re
import smtplib
import tempfile
import time
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from urllib.parse import urlsplit

import gradio as gr
import httpx

API_URL = os.getenv("PROTOCOL_API_URL", "http://127.0.0.1:8040").rstrip("/")
API_SECRET = os.getenv("PROTOCOL_WEBHOOK_SECRET", "change-me")
CONNECT_TIMEOUT = 12.0
POLL_SECONDS = 4          # live progress: how often the page asks the service where the review stands
SMTP_HOST = os.getenv("PROTOCOL_UI_SMTP_HOST", "")
SMTP_PORT = int(os.getenv("PROTOCOL_UI_SMTP_PORT", "587"))
SMTP_USER = os.getenv("PROTOCOL_UI_SMTP_USER", "")
SMTP_PASSWORD = os.getenv("PROTOCOL_UI_SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("PROTOCOL_UI_SMTP_FROM", "")
ALLOW_EMAIL = os.getenv("PROTOCOL_UI_ALLOW_EMAIL", "false").lower() == "true"

# Stage colours: the same ones as the research dashboard, so the two screens read as one system.
STAGE_COLORS = {"intake": "#5eead4", "administrative": "#ffc857", "scientific_reviewer": "#5cc8ff",
                "scientific_critic": "#b89cff", "revision": "#ff6b6b", "final": "#7bd389"}
STATIONS = [("intake", "Intake + validation"), ("administrative", "Administrative gate"),
            ("scientific_reviewer", "Scientific reviewer"), ("scientific_critic", "Critic"),
            ("revision", "Revision round"), ("final", "Decision + reports")]
AGENT_LABELS = {"coordinator": "Coordinator", "administrative": "Administrative agent",
                "scientific_reviewer": "Scientific reviewer", "scientific_critic": "Scientific critic"}
DECISIONS = {
    "PASS": ("#2e9d5b", "Screening criteria met",
             "The screening criteria were met. This is not an approval: the committee still reviews the protocol."),
    "NEEDS_HUMAN_REVIEW": ("#d9902b", "Needs human review",
                           "Some findings could not be confirmed automatically. A reviewer should read the findings marked "
                           "\"needs human review\" before the protocol moves on."),
    "MAJOR_CONCERNS": ("#d64545", "Major concerns",
                       "The review found substantial issues with located evidence. They should be resolved or answered before "
                       "committee review."),
    "RETURNED_ADMIN": ("#4c7fd1", "Returned to the submitter",
                       "The submission is not administratively complete, so it is returned to the submitter. The scientific "
                       "review starts once the missing items are provided."),
}
SEVERITY_COLORS = {"critical": "#d64545", "major": "#e0822b", "minor": "#4c7fd1", "info": "#7b8794"}
SEVERITY_ORDER = {"critical": 0, "major": 1, "minor": 2, "info": 3}
STATUS_VIEW = {"verified": ("#2e9d5b", "evidence located"), "unverified": ("#d9902b", "needs human review"),
               "revise": ("#d9902b", "needs human review"), "proposed": ("#d9902b", "needs human review"),
               "rejected": ("#7b8794", "rejected"), "withdrawn": ("#7b8794", "withdrawn")}
STATUS_FILTERS = {"All": None, "Evidence located (verified)": {"verified"},
                  "Needs human review": {"unverified", "revise", "proposed"}, "Rejected / withdrawn": {"rejected", "withdrawn"}}

CSS = """
:root{--brand:#183b5b;--accent:#0f766e;}
.gradio-container{max-width:1240px!important;margin:auto!important;font-family:Inter,'Segoe UI',Arial,sans-serif!important}
#hero{background:linear-gradient(110deg,#102b47,#214c6a);color:white;border-radius:14px;padding:14px 22px;margin-bottom:2px}
#hero .eyebrow{font-size:11px;letter-spacing:1.5px;color:#cbdce7}
#hero h1{color:white!important;font-size:22px!important;margin:2px 0 0!important}
#hero p{color:#d7e4ec!important;margin:3px 0 0!important;font-size:13.5px}
#hero .disclaimer{margin-top:9px;padding-top:8px;border-top:1px solid rgba(255,255,255,.18);font-size:12px;color:#b9cddb}
/* connection: a small status pill and a small button on one line */
#topbar{align-items:center!important;gap:10px!important;margin:2px 0 4px}
#topbar>div{min-width:0!important}
.pr-pill{display:inline-flex;align-items:center;gap:8px;border-radius:999px;padding:4px 14px;font-size:12.5px;border:1px solid var(--c);background:color-mix(in srgb,var(--c) 14%,transparent);color:var(--body-text-color)}
.pr-pill i{width:9px;height:9px;border-radius:50%;background:var(--c);display:inline-block}
.pr-pill span{opacity:.75}
.section-title{font-size:20px;font-weight:700;color:#15304b;margin:6px 0 12px}
.note{padding:9px 14px;border-left:3px solid #0f766e;background:color-mix(in srgb,#0f766e 13%,transparent);border-radius:8px;color:var(--body-text-color);font-size:13px}
#footer{font-size:12px;color:#64748b;margin:24px 0 0}

/* live progress: stage chips and the coloured agent log (colours of the research dashboard) */
.pr-head{font-size:14px;margin:2px 0 8px;color:var(--body-text-color)}
.pr-steps{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 12px}
.pr-step{flex:1;min-width:118px;text-align:center;padding:9px 6px;border-radius:10px;font-size:13px;line-height:1.25;
  border:1px solid var(--border-color-primary,#cbd5e1);color:var(--body-text-color-subdued,#64748b);background:transparent}
.pr-step small{display:block;font-size:10.5px;letter-spacing:.5px;opacity:.85}
.pr-step.done{border-color:var(--c);background:color-mix(in srgb,var(--c) 20%,transparent);color:var(--body-text-color)}
.pr-step.now{border-color:var(--c);background:var(--c);color:#0e1420;font-weight:700;animation:pr-pulse 1.4s infinite}
.pr-step.skip{opacity:.5;border-style:dashed}
@keyframes pr-pulse{0%,100%{box-shadow:0 0 0 0 color-mix(in srgb,var(--c) 70%,transparent)}50%{box-shadow:0 0 0 7px transparent}}
.pr-log{display:flex;flex-direction:column;gap:4px}
.pr-ev{border-left:4px solid var(--c);background:color-mix(in srgb,var(--c) 11%,transparent);border-radius:0 7px 7px 0;
  padding:5px 10px;font-size:13px;color:var(--body-text-color);display:flex;gap:9px;align-items:baseline}
.pr-ev .t{font-family:Consolas,monospace;font-size:12px;opacity:.7;white-space:nowrap}
.pr-ev .a{background:var(--c);color:#0e1420;border-radius:9px;padding:0 8px;font-size:11.5px;font-weight:700;white-space:nowrap}
.pr-ev .x{flex:1;word-break:break-word}
.pr-empty{padding:14px;border:1px dashed var(--border-color-primary,#cbd5e1);border-radius:10px;color:var(--body-text-color-subdued,#64748b);font-size:13px}

/* results: decision card, numbers, findings */
.pr-card{border-left:8px solid var(--c);background:color-mix(in srgb,var(--c) 13%,transparent);border-radius:12px;padding:18px 20px;color:var(--body-text-color)}
.pr-card .k{font-size:11.5px;letter-spacing:1px;opacity:.75}
.pr-card .d{display:inline-block;background:var(--c);color:#fff;border-radius:9px;padding:3px 14px;font-size:21px;font-weight:700;margin:7px 0 4px}
.pr-card .code{font-family:Consolas,monospace;font-size:12px;opacity:.7;margin-left:8px}
.pr-card p{margin:6px 0 0;font-size:14.5px}
.pr-card .meta{font-size:13px;opacity:.85;margin-top:8px}
.pr-card .warn{margin-top:10px;color:#d64545;font-weight:700}
.pr-kpis{display:flex;gap:10px;flex-wrap:wrap;margin-top:12px}
.pr-kpi{flex:1;min-width:120px;border:1px solid var(--border-color-primary,#cbd5e1);border-radius:10px;padding:10px 12px;text-align:center;color:var(--body-text-color)}
.pr-kpi b{display:block;font-size:26px;line-height:1.1;color:var(--c,inherit)}
.pr-kpi span{font-size:12px;opacity:.8}
.pr-legend{font-size:12.5px;color:var(--body-text-color-subdued,#64748b);margin:8px 0 6px}
.pr-f{border:1px solid var(--border-color-primary,#cbd5e1);border-left:5px solid var(--c);border-radius:8px;margin:5px 0;color:var(--body-text-color)}
.pr-f summary{cursor:pointer;padding:8px 10px;display:flex;gap:8px;align-items:center;flex-wrap:wrap;font-size:13.5px}
.pr-f summary .ti{flex:1;min-width:220px;font-weight:600}
.pr-f summary .pg{font-size:12px;opacity:.7;white-space:nowrap}
.pr-b{border-radius:9px;padding:1px 9px;font-size:11.5px;font-weight:700;color:#fff;background:var(--c);white-space:nowrap}
.pr-o{border-radius:9px;padding:0 8px;font-size:11.5px;border:1px solid var(--c);color:var(--body-text-color);white-space:nowrap}
.pr-o i{display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--c);margin-right:5px}
.pr-f .body{padding:4px 14px 12px;font-size:13.5px;line-height:1.5}
.pr-f .body h5{margin:9px 0 2px;font-size:11.5px;letter-spacing:.6px;text-transform:uppercase;opacity:.7}
.pr-f blockquote{margin:4px 0;padding:6px 10px;border-left:3px solid var(--border-color-primary,#cbd5e1);background:color-mix(in srgb,var(--body-text-color) 6%,transparent);border-radius:0 6px 6px 0;font-size:13px}
"""


def esc(x) -> str:
    return html_lib.escape("" if x is None else str(x))


def _check_local_api() -> None:
    parsed = urlsplit(API_URL)
    if parsed.scheme not in ("http", "https") or parsed.hostname not in ("127.0.0.1", "localhost", "::1"):
        raise ValueError("For this local prototype, PROTOCOL_API_URL must target localhost.")


def _request(method: str, endpoint: str, *, protected=False, **kwargs):
    _check_local_api()
    headers = kwargs.pop("headers", {})
    if protected:
        headers["X-Webhook-Secret"] = API_SECRET
    try:
        with httpx.Client(timeout=CONNECT_TIMEOUT if method == "GET" else 75.0, follow_redirects=False) as c:
            r = c.request(method, API_URL + endpoint, headers=headers, **kwargs)
            r.raise_for_status()
            return r
    except httpx.HTTPStatusError as exc:
        msg = exc.response.text[:400]
        raise gr.Error(f"Server returned {exc.response.status_code}: {msg}") from exc
    except httpx.RequestError as exc:
        raise gr.Error("Cannot connect to the local FastAPI service. Start it on port 8040.") from exc


def ping():
    """Connection status as a small pill: green when the local service answers, red otherwise."""
    try:
        data = _request("GET", "/health").json()
        mail = "automatic email off (dry-run)" if data.get("email_dry_run", True) else "AUTOMATIC EMAIL ON"
        return (f'<span class="pr-pill" style="--c:#2e9d5b"><i></i>Connected to the review service'
                f'<span>· model {esc(data.get("model", "-"))} · {esc(mail)}</span></span>')
    except Exception:
        return ('<span class="pr-pill" style="--c:#d64545"><i></i>Not connected'
                '<span>· start the review service on port 8040, then check again</span></span>')


# ------------------------------------------------------------------ results: decision card, numbers, findings
def _summary_html(d):
    """Decision card in the decision's colour, one plain sentence on what it means, and the four numbers."""
    decision = d.get("decision") or ""
    status = d.get("status") or ""
    if status == "failed" or not decision:
        color, label, sentence = "#7b8794", ("Review failed" if status == "failed" else "Pending"), (
            "The review did not finish (technical failure). No decision was produced; a person must review this protocol."
            if status == "failed" else "The review has not produced a decision yet.")
    else:
        color, label, sentence = DECISIONS.get(decision, ("#7b8794", decision, ""))
    if decision == "RETURNED_ADMIN" and d.get("force_scientific"):
        sentence += " (Evaluation run: the scientific review was run anyway, for information.)"
    by_status, by_sev = d.get("by_status") or {}, d.get("by_severity") or {}
    human = sum(by_status.get(k, 0) for k in ("unverified", "revise", "proposed"))
    score = d.get("score")
    failures = d.get("agent_failures") or []
    warn = (f'<div class="warn">An agent did not run ({esc(", ".join(failures))}). The review is incomplete: human review required.</div>'
            if failures or d.get("error") else "")
    kpis = [("Findings", d.get("n_findings", 0), ""), ("Evidence located", by_status.get("verified", 0), "#2e9d5b"),
            ("Need human review", human, "#d9902b"), ("Critical + major", by_sev.get("critical", 0) + by_sev.get("major", 0), "#d64545"),
            ("Score / 100", "-" if score is None else score, "")]
    tiles = "".join(f'<div class="pr-kpi" style="--c:{c or "inherit"}"><b>{esc(v)}</b><span>{esc(k)}</span></div>' for k, v, c in kpis)
    return (f'<div class="pr-card" style="--c:{color}"><div class="k">REVIEW OUTCOME · {esc(status)}</div>'
            f'<div><span class="d">{esc(label)}</span><span class="code">{esc(decision)}</span></div>'
            f'<p>{esc(sentence)}</p>'
            f'<div class="meta">Study: {esc(d.get("nct_id") or "not supplied")} · {esc(d.get("decision_rationale") or "")}</div>{warn}</div>'
            f'<div class="pr-kpis">{tiles}</div>')


def render_findings(findings, domain="All", severity="All", status="All"):
    """Findings as expandable rows with severity and status badges; three filters; most severe first."""
    findings = findings or []
    wanted = STATUS_FILTERS.get(status)
    shown = [f for f in findings
             if (domain == "All" or f.get("domain") == domain)
             and (severity == "All" or f.get("severity") == severity)
             and (wanted is None or f.get("status") in wanted)]
    shown.sort(key=lambda f: (SEVERITY_ORDER.get(f.get("severity"), 9), f.get("domain") or "", str(f.get("id") or "")))
    legend = ('<div class="pr-legend"><b>How to read the status.</b> "Evidence located" means the quoted passage was found on the '
              'cited page and the guideline code exists; "rule check" means a deterministic check of the document fired. Neither proves '
              f'that the finding is correct: every finding is read by a person. Showing {len(shown)} of {len(findings)} findings; click a row for the details.</div>')
    if not findings:
        return '<div class="pr-empty">No findings to show yet.</div>'
    rows = []
    for f in shown:
        sev = f.get("severity") or "info"
        scol = SEVERITY_COLORS.get(sev, "#7b8794")
        stcol, stlabel = STATUS_VIEW.get(f.get("status"), ("#7b8794", f.get("status") or "-"))
        if f.get("status") == "verified" and f.get("source") == "rule":     # a deterministic check fired: there is no quote to locate
            stlabel = "rule check"
        evidence = [e for e in (f.get("evidence") or []) if isinstance(e, dict)]
        pages = ", ".join(str(e.get("page")) for e in evidence if e.get("page"))
        quotes = "".join(f'<blockquote>p. {esc(e.get("page") or "?")}: {esc(e.get("quote") or "")}</blockquote>'
                         for e in evidence if e.get("quote")) or '<div style="opacity:.7">No quoted passage.</div>'
        title = f.get("title") or f.get("category") or ""
        if title.lower().startswith("issue raised by the critic"):      # generic title: show what the issue is
            title = "Critic: " + (f.get("description") or "")[:120]
        body = [f'<h5>What was found</h5>{esc(f.get("description") or f.get("title") or "")}', f'<h5>Evidence in the protocol</h5>{quotes}']
        if f.get("guideline_ref"):
            body.append(f'<h5>Guideline</h5>{esc(f.get("guideline_ref"))}')
        if f.get("recommendation"):
            body.append(f'<h5>Suggested action</h5>{esc(f.get("recommendation"))}')
        if f.get("critic_notes"):
            body.append(f'<h5>Why this status</h5>{esc(f.get("critic_notes"))}')
        rows.append(
            f'<details class="pr-f" style="--c:{scol}"><summary>'
            f'<span class="pr-b" style="--c:{scol}">{esc(sev)}</span>'
            f'<span class="pr-o" style="--c:{stcol}"><i></i>{esc(stlabel)}</span>'
            f'<span class="pr-o" style="--c:#7b8794">{esc(f.get("domain") or "")}</span>'
            f'<span class="ti">{esc(title)}</span>'
            f'<span class="pg">{esc(f.get("id") or "")}{" · p. " + esc(pages) if pages else ""}</span>'
            f'</summary><div class="body">{"".join(body)}</div></details>')
    return legend + "".join(rows)


def _pdf_reports(run_id, summary):
    """The PDF reports of a finished review, copied to a private temporary folder for download."""
    if summary.get("status") != "done":
        return None
    folder = Path(tempfile.mkdtemp(prefix="protocol_report_"))
    folder.chmod(0o700)
    name = re.sub(r"[^A-Za-z0-9_-]", "", summary.get("nct_id") or "") or "protocol"
    files = []
    for kind, label in (("final_report_pdf", "final_report"), ("administrative_report_pdf", "administrative_report"),
                        ("scientific_report_pdf", "scientific_report")):
        try:
            content = _request("GET", f"/runs/{run_id}/report?kind={kind}").content
        except Exception:       # the scientific report does not exist when the submission was returned at the gate
            continue
        out = folder / f"{name}_{label}.pdf"
        out.write_bytes(content)
        files.append(str(out))
    return files or None


def _read_summary(run_id):
    if not run_id: raise gr.Error("Select or start a review first.")
    summary = _request("GET",f"/runs/{run_id}/summary").json()
    detail = _request("GET",f"/runs/{run_id}").json()
    warning = ""
    if summary.get("status") not in ("done","failed"):
        warning = f"Review status: {summary.get('status')}. Refresh later."
    if summary.get("agent_failures") or summary.get("error"):
        warning += " Agent error detected: do not treat this review as PASS."
    if summary.get("decision") == "PASS" and (summary.get("agent_failures") or summary.get("error")):
        warning += " SAFETY WARNING: decision conflicts with error state."
    output = summary.get("final_summary") or summary.get("decision_rationale") or "No final narrative available yet."
    findings = (detail.get("state") or {}).get("findings") or []
    return summary, findings, _summary_html(summary), output, warning


def _results_bundle(run_id):
    """Everything the results tab shows for one review: card, summary text, findings, warning, states, PDFs, filters reset."""
    summary, findings, card, narrative, warning = _read_summary(run_id)
    reset = gr.update(value="All")
    return (card, narrative, render_findings(findings), warning, summary, findings, _pdf_reports(run_id, summary),
            reset, reset, reset)


def fetch_run(run_id):
    return _results_bundle(run_id)


def start_review(pdf_path, nct_id, confirmation):
    # The legacy backend may notify a configured address at the end of a review.
    # Only permit launching through this product when that pathway is in dry-run.
    # Email from this UI is exclusively initiated by the Send email button.
    health = _request("GET", "/health").json()
    if health.get("email_dry_run") is not True:
        raise gr.Error("Review not started: backend automatic email notifications are enabled. Set EMAIL_DRY_RUN=true on the FastAPI server and restart it. Email from this product must be sent manually.")
    if not confirmation:
        raise gr.Error("Confirm that you are authorized to submit this protocol and initiate a model run.")
    if not pdf_path:
        raise gr.Error("Upload a PDF before starting the review.")
    p = Path(pdf_path)
    if p.suffix.lower() != ".pdf" or p.stat().st_size > 60 * 1024 * 1024 or p.open("rb").read(5) != b"%PDF-":
        raise gr.Error("Choose a valid PDF file (maximum 60 MB).")
    nct_id = (nct_id or "").strip().upper()
    if nct_id and not re.fullmatch(r"NCT\d{8}", nct_id):
        raise gr.Error("NCT ID should be in the form NCT12345678, or left blank.")
    with p.open("rb") as f:
        data = _request("POST", "/webhook/protocol", protected=True,
                        files={"file":(p.name,f,"application/pdf")},
                        data={"nct_id":nct_id,"source":"gradio_product","config":"agents_full","force_scientific":"false"}).json()
    return data["run_id"],(f"Review started. Run ID: {data['run_id']}. This page follows the review live; the results open "
                           "automatically when it finishes (about one minute if the submission is returned at the administrative "
                           "gate, up to about eight minutes for a full review).")


# ------------------------------------------------------------------ live progress: stage chips + coloured agent log
def _event_stage(e) -> str:
    agent, event = e.get("agent") or "", e.get("event") or ""
    if agent == "coordinator":
        if event == "revise_round":
            return "revision"
        if event in ("decision", "reports_written", "notified"):
            return "final"
        return "intake"
    return agent if agent in STAGE_COLORS else "intake"


def _event_text(e) -> str:
    """One readable line per pipeline step or model call; no local paths, no addresses."""
    if e.get("kind") == "llm_call":
        return (f"model call finished · {e.get('input_tokens', 0):,} tokens in · {e.get('output_tokens', 0):,} out · "
                f"{round(e.get('duration_s') or 0)} s")
    event, detail = e.get("event") or "", e.get("detail") or ""
    if event == "notified":
        return "notification prepared (not sent automatically)"
    if event == "reports_written":
        return "reports written: final, administrative" + (", scientific" if "scientific_report" in detail else "")
    if event == "revise_round":
        return "the critic asked for a focused re-check: revision round " + (detail.replace("round=", "") or "1")
    if event == "decision":          # "RETURNED_ADMIN [reason]; Score: ..." -> the decision and its reason only
        return "decision: " + detail.split(";")[0].replace("[", "(").replace("]", ")")
    return (event.replace("_", " ") + (": " + detail if detail else ""))[:180]


def _elapsed(events, started_at, finished) -> int:
    stamps = [e.get("t") for e in events if e.get("t")]
    if finished and len(stamps) >= 2:
        try:
            return int((datetime.fromisoformat(stamps[-1]) - datetime.fromisoformat(stamps[0])).total_seconds())
        except ValueError:
            pass
    return int(time.time() - started_at) if started_at else 0


def progress_html(events, started_at=0.0, finished=False):
    """Stage chips (pending / running / done / not run) and the latest pipeline lines, each in its agent's colour."""
    steps = [e for e in (events or []) if e.get("kind") in ("step", "llm_call")]
    seen, current, in_revision = [], "intake", False
    for e in steps:
        stage = _event_stage(e)
        if stage == "revision":
            in_revision = True
        elif stage == "final":
            in_revision = False
        current = "revision" if in_revision and stage in ("scientific_reviewer", "scientific_critic", "revision") else stage
        for s in (stage, current):
            if s not in seen:
                seen.append(s)
    chips = []
    for n, (key, label) in enumerate(STATIONS, 1):
        if finished:
            state, note = ("done", "done") if key in seen else ("skip", "not run")
        elif key == current:
            state, note = "now", "running"
        elif key in seen:
            state, note = "done", "done"
        else:
            state, note = "todo", "waiting"
        chips.append(f'<div class="pr-step {state}" style="--c:{STAGE_COLORS[key]}"><small>STEP {n} · {note.upper()}</small>{esc(label)}</div>')
    secs = _elapsed(steps, started_at, finished)
    label = "finished" if finished else dict(STATIONS).get(current, current)
    head = f'<div class="pr-head">Current stage: <b>{esc(label)}</b> &nbsp;·&nbsp; elapsed {secs // 60}:{secs % 60:02d}</div>'
    lines = []
    for e in steps[-12:]:
        color = STAGE_COLORS[_event_stage(e)]
        agent = AGENT_LABELS.get(e.get("agent") or "", e.get("agent") or "")
        lines.append(f'<div class="pr-ev" style="--c:{color}"><span class="t">{esc((e.get("t") or "")[11:19])}</span>'
                     f'<span class="a">{esc(agent)}</span><span class="x">{esc(_event_text(e))}</span></div>')
    log = "".join(lines) or '<div class="pr-empty">Waiting for the first step ...</div>'
    return head + f'<div class="pr-steps">{"".join(chips)}</div><div class="pr-log">{log}</div>'


IDLE_PROGRESS = ('<div class="pr-steps">' + "".join(
    f'<div class="pr-step todo" style="--c:{STAGE_COLORS[k]}"><small>STEP {n}</small>{esc(label)}</div>' for n, (k, label) in enumerate(STATIONS, 1))
    + '</div><div class="pr-empty">The stages light up here, in each agent\'s colour, once a review is started.</div>')


def poll_review(run_id, started_at):
    """Timer tick while a review started from this page is running: refresh the live progress; when the review has
    finished, load its results, open the results tab and stop the timer. Read-only calls, no model call."""
    keep = gr.update()
    idle = (keep,) * 10
    if not run_id:
        return (keep, keep) + idle + (keep, gr.Timer(active=False))
    try:
        summary = _request("GET", f"/runs/{run_id}/summary").json()
        events = _request("GET", f"/stats/trace/{run_id}").json()
    except Exception:
        return (keep, '<div class="pr-empty">Waiting for the service ...</div>') + idle + (keep, keep)
    finished = summary.get("status") in ("done", "failed")
    progress = progress_html(events, started_at, finished)
    if not finished:
        return (keep, progress) + idle + (keep, keep)
    bundle = _results_bundle(run_id)
    done = (f"Review finished: {summary.get('decision') or summary.get('status')}. {summary.get('n_findings', 0)} findings. "
            "The results are open in the Review Results tab.")
    return (done, progress) + bundle + (gr.Tabs(selected="results"), gr.Timer(active=False))


def history():
    records = _request("GET","/runs?limit=100").json()
    options = []
    for r in records:
        rid=r.get("id") or r.get("run_id")
        if rid: options.append((f"{rid} | {r.get('status','')} | {r.get('nct_id','')}",rid))
    return gr.update(choices=options,value=None),f"{len(options)} local reviews available."


def get_report(run_id):
    if not run_id: raise gr.Error("Select a review first.")
    info = _request("GET",f"/runs/{run_id}/summary").json()
    if info.get("status") != "done": raise gr.Error("Reports are available after the review finishes.")
    result = _request("GET",f"/runs/{run_id}/report?kind=final").content
    # Export only to private OS temp folder, not an HTTP-served directory.
    folder=Path(tempfile.mkdtemp(prefix="protocol_report_"))
    folder.chmod(0o700)
    output=folder / "final_report.md"
    output.write_bytes(result)
    return str(output),"Report ready for download. Review content before sharing."


def prepare_email(run_id, recipient):
    if not run_id: raise gr.Error("Select a completed run first.")
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+",(recipient or "").strip()):
        raise gr.Error("Enter a valid recipient email address.")
    summary = _request("GET",f"/runs/{run_id}/summary").json()
    if summary.get("status") != "done": raise gr.Error("The review has not finished.")
    if not (summary.get("reports") or {}).get("final"):
        raise gr.Error("A final report is not available for this run.")
    subject = f"Clinical Protocol Review | {summary.get('nct_id') or run_id} | {summary.get('decision') or 'Review'}"
    body = (f"Protocol review summary\n\nStudy: {summary.get('nct_id') or '-'}\n"
            f"Decision: {summary.get('decision') or '-'}\n"
            f"Findings: {summary.get('n_findings', 0)}\n\n"
            "This is AI-assisted preliminary screening, not an ethics approval. "
            "Any unverified findings, unsupported claims or agent failures require human review.\n\n"
            f"Summary:\n{summary.get('final_summary') or ''}\n")
    return subject,body,"Preview generated. No email has been sent."


def send_email(run_id, recipient, subject, body, explicit_confirm):
    if not explicit_confirm: raise gr.Error("You must explicitly confirm this recipient and message before sending.")
    if not ALLOW_EMAIL:
        return "Email sending is disabled. Administrator must set PROTOCOL_UI_ALLOW_EMAIL=true and configure SMTP. No email sent."
    if not SMTP_HOST or not SMTP_FROM: raise gr.Error("SMTP is not configured. Nothing was sent.")
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+",(recipient or "").strip()):
        raise gr.Error("Invalid recipient address.")
    if not run_id: raise gr.Error("Select the run associated with this report.")
    summary=_request("GET",f"/runs/{run_id}/summary").json()
    if summary.get("status") != "done" or not (summary.get("reports") or {}).get("final"):
        raise gr.Error("No completed report is available for the selected run.")
    report = _request("GET",f"/runs/{run_id}/report?kind=final").content
    msg=EmailMessage()
    msg["From"]=SMTP_FROM; msg["To"]=recipient.strip(); msg["Subject"]=(subject or "Clinical Protocol Review")[:180]
    msg.set_content(body or "")
    msg.add_attachment(report, maintype="text", subtype="markdown", filename="final_report.md")
    try:
        with smtplib.SMTP(SMTP_HOST,SMTP_PORT,timeout=20) as client:
            client.starttls()
            if SMTP_USER: client.login(SMTP_USER,SMTP_PASSWORD)
            client.send_message(msg)
    except Exception as exc:
        raise gr.Error(f"Email delivery failed: {type(exc).__name__}. Please check SMTP settings.") from exc
    return "Email sent to the confirmed recipient with the final Markdown report attached."


with gr.Blocks(title="Clinical Protocol Review") as demo:
    gr.HTML("<div id='hero'><div class='eyebrow'>CLINICAL RESEARCH · AI-ASSISTED SCREENING</div><h1>Clinical Protocol Review</h1>"
            "<p>Structured protocol screening, evidence-linked findings and human oversight.</p>"
            "<div class='disclaimer'>Decision support only. Not an IRB approval, clinical validation or substitute for expert judgment. "
            "Do not upload confidential hospital protocols without organizational authorization.</div></div>")
    with gr.Row(elem_id="topbar"):
        connected=gr.HTML('<span class="pr-pill" style="--c:#7b8794"><i></i>Checking the connection ...</span>')
        check=gr.Button("Check connection",variant="secondary",size="sm",scale=0,min_width=150)
    check.click(ping,outputs=connected)
    demo.load(ping,outputs=connected)      # checked on every page load, not once at import time
    run_state=gr.State("")
    summary_state=gr.State({})
    findings_state=gr.State([])
    started_state=gr.State(0.0)
    with gr.Tabs() as tabs:
        with gr.Tab("New Review",id="new"):
            gr.Markdown("### Start a protocol review")
            gr.Markdown("Only the full review workflow is available here. Experimental configurations and administrative gate bypass are intentionally hidden.")
            with gr.Row():
                with gr.Column(scale=2):
                    uploaded=gr.File(label="Clinical study protocol (PDF)",file_types=[".pdf"],type="filepath")
                    nct=gr.Textbox(label="ClinicalTrials.gov ID (optional)",placeholder="NCT12345678")
                    authorized=gr.Checkbox(label="I confirm I am authorized to process this document and understand this starts a paid LLM review.")
                    start=gr.Button("Start full protocol review",variant="primary")
                    start_feedback=gr.Textbox(label="Run status",interactive=False)
                with gr.Column(scale=1):
                    gr.Markdown("### What happens next?\n1. Intake and document checks\n2. Administrative screening\n3. Scientific review, when applicable\n4. Critic and evidence checks\n5. Decision support report\n\n**Important:** a failed agent requires human review. A technical failure must never mean PASS.")
            gr.Markdown("### Live progress\nThe stages and the agents' steps appear here while the review runs; the page refreshes by itself every few seconds.")
            progress=gr.HTML(IDLE_PROGRESS)
            timer=gr.Timer(POLL_SECONDS,active=False)
        with gr.Tab("Review Results",id="results"):
            gr.Markdown("### Review outcome and findings")
            with gr.Row():
                past=gr.Dropdown(label="Previously saved reviews",choices=[],interactive=True,scale=4)
                refresh=gr.Button("Refresh history",size="sm",scale=0,min_width=150)
            history_message=gr.Markdown()
            refresh.click(history,outputs=[past,history_message])
            past.change(lambda v:v or "",inputs=past,outputs=run_state)
            with gr.Row():
                manual_id=gr.Textbox(label="Or enter an existing Run ID",placeholder="run-id",scale=4)
                load=gr.Button("Load review results",variant="primary",size="sm",scale=0,min_width=190)
            overview=gr.HTML('<div class="note">Choose a saved review or enter a Run ID.</div>')
            warning=gr.Markdown()
            pdf_reports=gr.File(label="Reports (PDF): final, administrative, scientific",file_count="multiple",interactive=False)
            narrative=gr.Textbox(label="Executive summary",lines=9,max_lines=80,interactive=False)   # grows with the text, never cut
            gr.Markdown("### Evidence-linked findings")
            with gr.Row():
                f_domain=gr.Dropdown(["All","administrative","scientific"],value="All",label="Domain",filterable=False)
                f_severity=gr.Dropdown(["All","critical","major","minor","info"],value="All",label="Severity",filterable=False)
                f_status=gr.Dropdown(list(STATUS_FILTERS),value="All",label="Status",filterable=False)
            findings_view=gr.HTML('<div class="pr-empty">No findings to show yet.</div>')
            for flt in (f_domain,f_severity,f_status):
                flt.change(render_findings,inputs=[findings_state,f_domain,f_severity,f_status],outputs=findings_view)
            results_out=[overview,narrative,findings_view,warning,summary_state,findings_state,pdf_reports,f_domain,f_severity,f_status]
            get_run=lambda rid1,rid2: (rid2 or rid1 or "").strip()
            load.click(get_run,inputs=[run_state,manual_id],outputs=run_state).then(fetch_run,inputs=run_state,outputs=results_out)
        with gr.Tab("Reports & Email",id="reports"):
            gr.Markdown("### Share a completed review")
            gr.Markdown("Reports are **never emailed automatically** by this product. To share one, select a recipient, preview the message, review the report, confirm, and click **Send email**. Sending requires approved SMTP configuration.")
            with gr.Row():
                export=gr.Button("Prepare final report for download",size="sm",scale=0,min_width=270)
            report_file=gr.File(label="Download final report",interactive=False)
            export_status=gr.Textbox(label="Report status",interactive=False)
            export.click(get_report,inputs=run_state,outputs=[report_file,export_status])
            gr.Markdown("### Email preview")
            recipient=gr.Textbox(label="Recipient email",placeholder="research.team@your-organization.org")
            with gr.Row():
                preview=gr.Button("Generate email preview",size="sm",scale=0,min_width=210)
            subject=gr.Textbox(label="Subject")
            email_body=gr.Textbox(label="Message (editable)",lines=8,max_lines=60)
            email_status=gr.Textbox(label="Email status",interactive=False)
            preview.click(prepare_email,inputs=[run_state,recipient],outputs=[subject,email_body,email_status])
            email_confirm=gr.Checkbox(label="I reviewed the recipient, message and attached report, and explicitly authorize sending this email.")
            with gr.Row():
                send=gr.Button("Send email",variant="primary",size="sm",scale=0,min_width=150)
            # Any modification invalidates the previous approval. Confirmation is
            # required for the exact recipient, message and selected review.
            for field in (recipient, subject, email_body, run_state):
                field.change(lambda: False, outputs=email_confirm)
            send.click(send_email,inputs=[run_state,recipient,subject,email_body,email_confirm],outputs=email_status)
        with gr.Tab("About",id="about"):
            gr.Markdown("### Designed for clinical research teams\nThis product is a user-facing layer over the project's existing FastAPI and Multi-Agent review engine. It does not expose evaluation configurations or model costs to end users.\n\n**What the output means**\n- PASS means screening criteria were met, not that the study is approved.\n- RETURNED_ADMIN flags administrative issues.\n- NEEDS_HUMAN_REVIEW requires human assessment.\n- MAJOR_CONCERNS flags substantial issues.\n- 'Verified' is a technical system status. It does not guarantee that the finding is correct or that the quote supports it.\n\n**Deployment**\nUse on localhost for demonstration. Organizational authentication, access controls, data retention policies, and approved email integration are required before real hospital deployment.")
    # Live follow-up of a review started from this page: the timer runs only between the click and the end of the review.
    start.click(start_review,inputs=[uploaded,nct,authorized],outputs=[run_state,start_feedback]).success(
        lambda: (time.time(),progress_html([],time.time()),gr.Timer(active=True)),outputs=[started_state,progress,timer])
    timer.tick(poll_review,inputs=[run_state,started_state],outputs=[start_feedback,progress]+results_out+[tabs,timer])
    gr.HTML("<div id='footer'>Clinical Protocol Review · Research prototype · Decision support only · No model calls until Start full protocol review is clicked.</div>")

if __name__=="__main__":
    demo.launch(server_name="127.0.0.1",server_port=int(os.getenv("PROTOCOL_UI_PORT","7860")),share=False,show_error=False,css=CSS,theme=gr.themes.Soft(primary_hue="blue",secondary_hue="teal"))
