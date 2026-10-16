"""Protocols arriving by email: poll an IMAP inbox, pick PDF attachments, run the review.

Alternative to the webhook when no Make/n8n automation is available.
"""
from __future__ import annotations

import email
import imaplib
import logging
import re
import time
from email.header import decode_header
from pathlib import Path

from ..config import PROJECT_ROOT, settings
from ..pipeline import new_run_id, run_review

log = logging.getLogger(__name__)
UPLOAD_DIR = PROJECT_ROOT / "data" / "uploads"
NCT_RE = re.compile(r"\bNCT\d{8}\b")


def _decode(s: str | None) -> str:
    if not s:
        return ""
    parts = decode_header(s)
    return "".join(p.decode(enc or "utf-8", errors="replace") if isinstance(p, bytes) else p for p, enc in parts)


def extract_pdfs(msg: email.message.Message) -> list[tuple[str, bytes]]:
    out = []
    for part in msg.walk():
        name = _decode(part.get_filename())
        ctype = part.get_content_type()
        if name.lower().endswith(".pdf") or ctype == "application/pdf":
            data = part.get_payload(decode=True)
            if data and data[:5].startswith(b"%PDF"):
                out.append((name or "protocol.pdf", data))
    return out


def process_message(raw: bytes) -> list[str]:
    msg = email.message_from_bytes(raw)
    sender = _decode(msg.get("From"))
    subject = _decode(msg.get("Subject"))
    nct = NCT_RE.search(subject or "")
    run_ids = []
    for name, data in extract_pdfs(msg):
        run_id = new_run_id()
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        path = UPLOAD_DIR / f"{run_id}_{Path(name).stem[:60]}.pdf"
        path.write_bytes(data)
        log.info("email from %s: '%s' -> %s", sender, subject, path.name)
        run_review(path, source="email", submitter=sender, nct_id=nct.group(0) if nct else "", run_id=run_id)
        run_ids.append(run_id)
    return run_ids


def poll_once() -> list[str]:
    if not settings.imap_host:
        raise RuntimeError("IMAP_HOST not configured")
    processed: list[str] = []
    with imaplib.IMAP4_SSL(settings.imap_host) as box:
        box.login(settings.imap_user, settings.imap_password)
        box.select(settings.imap_folder)
        status, data = box.search(None, "UNSEEN")
        if status != "OK":
            return processed
        for num in data[0].split():
            status, parts = box.fetch(num, "(RFC822)")
            if status != "OK" or not parts or not isinstance(parts[0], tuple):
                continue
            try:
                processed += process_message(parts[0][1])
            except Exception:
                log.exception("failed to process message %s", num)
            box.store(num, "+FLAGS", "\\Seen")
    return processed


def poll_forever():
    log.info("polling %s every %ss", settings.imap_host, settings.imap_poll_seconds)
    while True:
        try:
            ids = poll_once()
            if ids:
                log.info("started runs: %s", ids)
        except Exception:
            log.exception("poll failed")
        time.sleep(settings.imap_poll_seconds)
