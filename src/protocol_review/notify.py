"""Email notifications to the committee coordinator ("the boss")."""
from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from pathlib import Path

from .config import settings
from .reports import run_dir
from .scoring import score_line
from .state import Decision, ReviewState

log = logging.getLogger(__name__)

SUBJECTS = {
    Decision.RETURNED_ADMIN.value: "[Protocol Review] RETURNED - incomplete submission",
    Decision.MAJOR_CONCERNS.value: "[Protocol Review] MAJOR CONCERNS - action needed before committee",
    Decision.NEEDS_HUMAN_REVIEW.value: "[Protocol Review] NEEDS HUMAN REVIEW - unverified findings",
    Decision.PASS.value: "[Protocol Review] PASS - ready for committee",
}


def build_message(to: str, subject: str, body: str, attachments: list[Path]) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = settings.smtp_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    for p in attachments:
        if p.exists():
            msg.add_attachment(p.read_bytes(), maintype="text", subtype="markdown", filename=p.name)
    return msg


def send_email(to: str, subject: str, body: str, attachments: list[Path] | None = None, run_id: str = "") -> str:
    """Send (or, in dry-run mode, write an .eml file). Returns a human-readable status."""
    msg = build_message(to, subject, body, attachments or [])
    if settings.email_dry_run or not settings.smtp_host:
        target = (run_dir(run_id) if run_id else settings.output_path) / "email.eml"
        target.write_bytes(bytes(msg))
        return f"dry-run: email to {to} written to {target}"
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as s:
        s.starttls()
        if settings.smtp_user:
            s.login(settings.smtp_user, settings.smtp_password)
        s.send_message(msg)
    return f"sent to {to}"


def notify_boss(state: ReviewState) -> list[str]:
    decision = state.get("decision") or ""
    meta = state.get("protocol_meta") or {}
    subject = SUBJECTS.get(decision, "[Protocol Review] Review complete") + f" - {meta.get('title', '')[:80]}"
    paths = state.get("report_paths") or {}
    attachments = [Path(paths[k]) for k in ("final_report", "administrative_report", "scientific_report") if k in paths]
    body = (f"Protocol review completed (run {state.get('run_id')}).\n"
            f"Decision: {decision}\n{score_line(state.get('score'))}\n\n{state.get('final_summary', '')}\n\n"
            f"Reports attached: {', '.join(p.name for p in attachments)}\n")
    if state.get("errors"):
        body += "\nWarnings during the run:\n" + "\n".join(f"- {e}" for e in state["errors"]) + "\n"
    try:
        status = send_email(settings.boss_email, subject, body, attachments, run_id=state.get("run_id", ""))
    except Exception as exc:  # never fail the run because of SMTP
        log.exception("email failed")
        status = f"email FAILED: {exc}"
    return [status]
