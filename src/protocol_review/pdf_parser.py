"""PDF text extraction (PyMuPDF) and light deterministic metadata extraction."""
from __future__ import annotations

import re
from pathlib import Path

import pymupdf as fitz

NCT_RE = re.compile(r"\bNCT\d{8}\b")
VERSION_RE = re.compile(r"(?:protocol\s+)?version\s*[:#]?\s*v?(\d+(?:\.\d+)*)", re.I)
DATE_RE = re.compile(
    r"\b(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}"
    r"|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}"
    r"|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})\b",
    re.I,
)
PI_RE = re.compile(r"principal\s+investigator\s*[:\-]?\s*([A-Z][\w.\-' ]{3,80})", re.I)
SPONSOR_RE = re.compile(r"\bsponsor\s*[:\-]\s*([A-Z][\w&.,\-' ]{3,100})", re.I)
PHASE_RE = re.compile(r"\bphase\s+(I{1,3}V?|IV|[1-4](?:/[1-4])?|[1-4][ab]?)\b", re.I)


def extract_pages(pdf_path: str | Path) -> list[dict]:
    """Return [{'page': 1-based, 'text': str}] for every page."""
    pages: list[dict] = []
    with fitz.open(str(pdf_path)) as doc:
        for i, page in enumerate(doc, start=1):
            pages.append({"page": i, "text": page.get_text("text")})
    return pages


def pages_to_text(pages: list[dict]) -> str:
    """Join pages with explicit markers so agents can cite page numbers."""
    return "\n".join(f"\n=== PAGE {p['page']} ===\n{p['text']}" for p in pages)


def extract_metadata(pages: list[dict]) -> dict:
    """Cheap regex metadata used by rule checks and shown to agents."""
    text = "\n".join(p["text"] for p in pages)
    first = "\n".join(p["text"] for p in pages[:2])
    title = ""
    for line in first.splitlines():
        s = line.strip()
        if len(s) > 15 and not s.lower().startswith(("version", "date", "protocol number")):
            title = s[:200]
            break
    ncts = sorted(set(NCT_RE.findall(text)))
    ver = VERSION_RE.search(first) or VERSION_RE.search(text)
    date = DATE_RE.search(first)
    pi = PI_RE.search(text)
    sponsor = SPONSOR_RE.search(text)
    phase = PHASE_RE.search(text)
    total_chars = sum(len(p["text"].strip()) for p in pages)
    likely_scanned = total_chars < 40 * max(1, len(pages))
    return {
        "title": title,
        "nct_ids": ncts,
        "nct_id": ncts[0] if ncts else "",
        "version": ver.group(1) if ver else "",
        "date": date.group(1) if date else "",
        "principal_investigator": pi.group(1).strip() if pi else "",
        "sponsor": sponsor.group(1).strip() if sponsor else "",
        "phase": phase.group(1).upper() if phase else "",
        "page_count": len(pages),
        "char_count": len(text),
        "likely_scanned": likely_scanned,
    }


def parse_pdf(pdf_path: str | Path) -> dict:
    pages = extract_pages(pdf_path)
    return {"pages": pages, "pdf_text": pages_to_text(pages), "protocol_meta": extract_metadata(pages)}
