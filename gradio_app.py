"""End-user Gradio frontend for the existing Clinical Protocol Review FastAPI service.

No changes to the agent graph, pipeline, evaluation data or database schema.
Launch FastAPI first on http://127.0.0.1:8040, then run this file.
"""
from __future__ import annotations

import os
import re
import smtplib
import tempfile
import time
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

CSS = """
:root{--brand:#183b5b;--accent:#0f766e;}
.gradio-container{max-width:1240px!important;margin:auto!important;font-family:Inter,'Segoe UI',Arial,sans-serif!important}
#hero{background:linear-gradient(110deg,#102b47,#214c6a);color:white;border-radius:18px;padding:24px 28px;margin-bottom:10px}
#hero h1{color:white!important;font-size:27px!important;margin:0!important}
#hero p{color:#d7e4ec!important;margin:7px 0 0!important}
.section-title{font-size:20px;font-weight:700;color:#15304b;margin:6px 0 12px}
.note{padding:12px 16px;border-left:3px solid #0f766e;background:#f1f7f7;border-radius:8px;color:#305261}
#footer{font-size:12px;color:#64748b;margin:24px 0 0}
"""


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
    try:
        data = _request("GET", "/health").json()
        return f"Connected to local server | Model: {data.get('model','-')} | Email dry-run: {data.get('email_dry_run', True)}"
    except Exception as exc:
        return f"Not connected: {exc}"


def _summary_html(d):
    def esc(x):
        import html
        return html.escape("" if x is None else str(x))
    decision = d.get("decision") or "Pending"
    score = d.get("score")
    nct = d.get("nct_id") or "Not supplied"
    warnings = d.get("agent_failures") or []
    warn = '<div style="margin-top:14px;color:#9a3412;font-weight:600">Agent failure detected. Human review required.</div>' if warnings else ""
    return (f'<div style="padding:21px;background:#f5f9fc;border-radius:14px;border:1px solid #dbe5eb">'
            f'<div style="font-size:12px;color:#49677e">REVIEW OUTCOME · {esc(d.get("status"))}</div>'
            f'<h2 style="color:#143b59;margin:7px 0">{esc(decision)}</h2>'
            f'<div style="color:#334155">Study: {esc(nct)} · Score: {esc(score if score is not None else "Not available")}'
            f' · Findings: {esc(d.get("n_findings",0))}</div>{warn}</div>')


def _findings_rows(data):
    state = data.get("state") or {}
    fs = state.get("findings") or []
    rows=[]
    for f in fs:
        evidence = f.get("evidence") or []
        pages = ", ".join(str(e.get("page", "")) for e in evidence if isinstance(e,dict))
        quote = " | ".join(str(e.get("quote", "")) for e in evidence if isinstance(e,dict))
        rows.append([str(f.get("domain") or ""),str(f.get("severity") or ""),str(f.get("status") or ""),
                     str(f.get("title") or f.get("category") or ""),pages,str(f.get("guideline_ref") or ""),quote[:350]])
    return rows


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
    return summary, detail, _summary_html(summary), output, _findings_rows(detail), warning


def fetch_run(run_id):
    summary, detail, html, narrative, rows, warning = _read_summary(run_id)
    return html, narrative, rows, warning, summary


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


STAGES = [("coordinator", "intake", "1. Intake and document checks"),
          ("administrative", None, "2. Administrative screening"),
          ("scientific_reviewer", None, "3. Scientific review"),
          ("scientific_critic", None, "4. Critic and evidence checks"),
          ("coordinator", "decision", "5. Decision and reports")]


def _progress_text(events, started_at):
    """Plain-text view of where the review stands, from the service's trace (pipeline steps and LLM calls)."""
    stage, rounds = STAGES[0][2], 0
    lines = []
    for e in events:
        agent, kind, event = e.get("agent") or "", e.get("kind"), e.get("event") or ""
        clock = (e.get("t") or "")[11:19]
        if kind == "step":
            if agent == "coordinator" and event == "revise_round":
                rounds += 1
            for a, ev, label in STAGES:
                if agent == a and (ev is None or event == ev or (ev == "decision" and event in ("decision", "reports_written", "notified"))):
                    stage = label + (f" (revision round {rounds})" if rounds and a.startswith("scientific") else "")
            lines.append(f"{clock}  {agent}: {event} {(e.get('detail') or '')[:110]}".rstrip())
        elif kind == "llm_call":
            lines.append(f"{clock}  {agent}: model call finished ({e.get('input_tokens', 0):,} tokens in, "
                         f"{e.get('output_tokens', 0):,} out, {round(e.get('duration_s') or 0)} s)")
    elapsed = int(time.time() - started_at) if started_at else 0
    head = f"Current stage: {stage}   |   elapsed {elapsed // 60}:{elapsed % 60:02d}"
    return head + "\n\n" + "\n".join(lines[-9:])


def poll_review(run_id, started_at):
    """Timer tick while a review started from this page is running: refresh the live progress; when the review has
    finished, load its results, open the results tab and stop the timer. Read-only calls, no model call."""
    keep = gr.update()
    if not run_id:
        return keep, keep, keep, keep, keep, keep, keep, keep, gr.Timer(active=False)
    try:
        summary = _request("GET", f"/runs/{run_id}/summary").json()
        events = _request("GET", f"/stats/trace/{run_id}").json()
    except Exception:
        return keep, "Waiting for the service ...", keep, keep, keep, keep, keep, keep, keep
    progress = _progress_text(events, started_at)
    if summary.get("status") not in ("done", "failed"):
        return keep, progress, keep, keep, keep, keep, keep, keep, keep
    summary, detail, html, narrative, rows, warning = _read_summary(run_id)
    done = (f"Review finished: {summary.get('decision') or summary.get('status')}. {summary.get('n_findings', 0)} findings. "
            "The results are open in the Review Results tab.")
    return done, progress, html, narrative, rows, warning, summary, gr.Tabs(selected="results"), gr.Timer(active=False)


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
    gr.HTML("<div id='hero'><div style='font-size:12px;letter-spacing:1.5px;color:#cbdce7'>CLINICAL RESEARCH · AI-ASSISTED SCREENING</div><h1>Clinical Protocol Review</h1><p>Structured protocol screening, evidence-linked findings and human oversight.</p></div>")
    gr.HTML("<div class='note'>Decision support only. Not an IRB approval, clinical validation or substitute for expert judgment. Do not upload confidential hospital protocols without organizational authorization.</div>")
    connected=gr.Textbox(label="Local service connection",interactive=False)
    gr.Button("Check connection",variant="secondary",size="sm").click(ping,outputs=connected)
    demo.load(ping,outputs=connected)      # checked on every page load, not once at import time
    run_state=gr.State("")
    summary_state=gr.State({})
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
                    progress=gr.Textbox(label="Live progress (updates every few seconds while a review is running)",lines=12,interactive=False)
                    timer=gr.Timer(POLL_SECONDS,active=False)
                with gr.Column(scale=1):
                    gr.Markdown("### What happens next?\n1. Intake and document checks\n2. Administrative screening\n3. Scientific review, when applicable\n4. Critic and evidence checks\n5. Decision support report\n\n**Important:** a failed agent requires human review. A technical failure must never mean PASS.")
        with gr.Tab("Review Results",id="results"):
            gr.Markdown("### Review outcome and findings")
            with gr.Row():
                past=gr.Dropdown(label="Previously saved reviews",choices=[],interactive=True,scale=4)
                refresh=gr.Button("Refresh history",scale=1)
            history_message=gr.Markdown()
            refresh.click(history,outputs=[past,history_message])
            past.change(lambda v:v or "",inputs=past,outputs=run_state)
            manual_id=gr.Textbox(label="Or enter an existing Run ID",placeholder="run-id")
            load=gr.Button("Load review results",variant="primary")
            overview=gr.HTML('<div class="note">Choose a saved review or enter a Run ID.</div>')
            warning=gr.Markdown()
            narrative=gr.Textbox(label="Executive summary",lines=9,max_lines=80,interactive=False)   # grows with the text, never cut
            finding_table=gr.Dataframe(headers=["Domain","Severity","Verification","Finding","Page(s)","Guideline","Evidence excerpt"],datatype=["str"]*7,interactive=False,wrap=True,label="Evidence-linked findings")
            get_run=lambda rid1,rid2: (rid2 or rid1 or "").strip()
            load.click(get_run,inputs=[run_state,manual_id],outputs=run_state).then(fetch_run,inputs=run_state,outputs=[overview,narrative,finding_table,warning,summary_state])
        with gr.Tab("Reports & Email",id="reports"):
            gr.Markdown("### Share a completed review")
            gr.Markdown("Reports are **never emailed automatically** by this product. To share one, select a recipient, preview the message, review the report, confirm, and click **Send email**. Sending requires approved SMTP configuration.")
            export=gr.Button("Prepare final report for download")
            report_file=gr.File(label="Download final report",interactive=False)
            export_status=gr.Textbox(label="Report status",interactive=False)
            export.click(get_report,inputs=run_state,outputs=[report_file,export_status])
            gr.Markdown("### Email preview")
            recipient=gr.Textbox(label="Recipient email",placeholder="research.team@your-organization.org")
            preview=gr.Button("Generate email preview")
            subject=gr.Textbox(label="Subject")
            email_body=gr.Textbox(label="Message (editable)",lines=8,max_lines=60)
            email_status=gr.Textbox(label="Email status",interactive=False)
            preview.click(prepare_email,inputs=[run_state,recipient],outputs=[subject,email_body,email_status])
            email_confirm=gr.Checkbox(label="I reviewed the recipient, message and attached report, and explicitly authorize sending this email.")
            send=gr.Button("Send email",variant="primary")
            # Any modification invalidates the previous approval. Confirmation is
            # required for the exact recipient, message and selected review.
            for field in (recipient, subject, email_body, run_state):
                field.change(lambda: False, outputs=email_confirm)
            send.click(send_email,inputs=[run_state,recipient,subject,email_body,email_confirm],outputs=email_status)
        with gr.Tab("About",id="about"):
            gr.Markdown("### Designed for clinical research teams\nThis product is a user-facing layer over the project's existing FastAPI and Multi-Agent review engine. It does not expose evaluation configurations or model costs to end users.\n\n**What the output means**\n- PASS means screening criteria were met, not that the study is approved.\n- RETURNED_ADMIN flags administrative issues.\n- NEEDS_HUMAN_REVIEW requires human assessment.\n- MAJOR_CONCERNS flags substantial issues.\n- 'Verified' is a technical system status. It does not guarantee that the finding is correct or that the quote supports it.\n\n**Deployment**\nUse on localhost for demonstration. Organizational authentication, access controls, data retention policies, and approved email integration are required before real hospital deployment.")
    # Live follow-up of a review started from this page: the timer runs only between the click and the end of the review.
    start.click(start_review,inputs=[uploaded,nct,authorized],outputs=[run_state,start_feedback]).success(
        lambda: (time.time(),"Review accepted by the service ...",gr.Timer(active=True)),outputs=[started_state,progress,timer])
    timer.tick(poll_review,inputs=[run_state,started_state],
               outputs=[start_feedback,progress,overview,narrative,finding_table,warning,summary_state,tabs,timer])
    gr.HTML("<div id='footer'>Clinical Protocol Review · Research prototype · Decision support only · No model calls until Start full protocol review is clicked.</div>")

if __name__=="__main__":
    demo.launch(server_name="127.0.0.1",server_port=int(os.getenv("PROTOCOL_UI_PORT","7860")),share=False,show_error=False,css=CSS,theme=gr.themes.Soft(primary_hue="blue",secondary_hue="teal"))
