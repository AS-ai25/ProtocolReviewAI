"""Structured protocol JSON (charter v1.3, item 1) and the JSON Validation Tool.

The Coordinator builds ONE structured object from the PDF at intake:

    {
      "schema_version": "1.0",
      "source": {"pdf_path", "sha256", "page_count"},
      "metadata": {... regex metadata ...},
      "sections": [{"index", "number", "title", "page_start", "page_end", "text", "char_count"}],
      "pages": [{"page", "char_count", "section_indexes"}]
    }

It carries the ORIGINAL text, organised by protocol sections with page references,
and is immutable after intake: every later agent only appends its own results to
other ReviewState keys. `validate_protocol_json` is the deterministic JSON
Validation Tool that runs before the Administrative Review Agent.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

SCHEMA_VERSION = "1.0"

# Headings like "1. Background", "2.3 Objectives", "12) Statistics", "APPENDIX A"
NUMBERED_RE = re.compile(r"^\s*(\d{1,2}(?:\.\d{1,2}){0,2})[.)]?\s+([A-Z][A-Za-z0-9 ,/&()\-']{2,80})\s*$")
APPENDIX_RE = re.compile(r"^\s*(APPENDIX|Appendix|ANNEX|Annex)\s+([A-Z0-9]{1,3})\b[:.\- ]*(.{0,80})$")
KNOWN_TITLES = (
    "background", "rationale", "introduction", "objective", "hypothes", "design", "eligibility", "inclusion", "exclusion",
    "intervention", "outcome", "endpoint", "timeline", "schedule", "sample size", "recruitment", "randomi", "allocation",
    "blinding", "masking", "data collection", "data management", "statistic", "analysis", "monitoring", "harms",
    "adverse", "safety", "auditing", "ethic", "consent", "confidentiality", "dissemination", "references", "appendix",
)
TITLE_ONLY_RE = re.compile(r"^\s*([A-Z][A-Za-z ,/&()\-']{3,60})\s*$")


def _is_heading(line: str) -> tuple[str, str, str] | None:
    """-> (number, title, heading as printed in the protocol) or None."""
    m = NUMBERED_RE.match(line)
    if m:
        return m.group(1), m.group(2).strip(), " ".join(line.split())
    m = APPENDIX_RE.match(line)
    if m:
        label = f"{m.group(1).title()} {m.group(2)}"
        return label, (m.group(3) or "").strip() or label, " ".join(line.split())
    m = TITLE_ONLY_RE.match(line)
    if m and len(line.split()) <= 6:
        low = line.lower()
        if any(k in low for k in KNOWN_TITLES):
            return "", m.group(1).strip(), m.group(1).strip()
    return None


def build_protocol_json(pages: list[dict], meta: dict, pdf_path: str | Path = "") -> dict:
    sections: list[dict] = []
    current = {"index": 0, "number": "", "title": "Front matter", "heading": "Front matter", "page_start": 1, "page_end": 1, "lines": []}
    for p in pages:
        for line in p["text"].splitlines():
            head = _is_heading(line)
            if head and current["lines"] is not None and (current["lines"] or sections):
                current["page_end"] = p["page"]
                sections.append(current)
                current = {"index": len(sections), "number": head[0], "title": head[1], "heading": head[2],
                           "page_start": p["page"], "page_end": p["page"], "lines": []}
                continue
            if head and not current["lines"] and not sections:  # heading as the very first line
                current.update({"number": head[0], "title": head[1], "heading": head[2], "page_start": p["page"]})
                continue
            current["lines"].append(line)
            current["page_end"] = p["page"]
    sections.append(current)
    out_sections = []
    for s in sections:
        text = "\n".join(s["lines"]).strip()
        out_sections.append({
            "index": s["index"], "number": s["number"], "title": s["title"],
            "heading": s["heading"],
            "page_start": s["page_start"], "page_end": s["page_end"], "text": text, "char_count": len(text),
        })
    page_rows = []
    for p in pages:
        idx = [s["index"] for s in out_sections if s["page_start"] <= p["page"] <= s["page_end"]]
        page_rows.append({"page": p["page"], "char_count": len(p["text"]), "section_indexes": idx})
    sha = ""
    if pdf_path and Path(pdf_path).exists():
        sha = hashlib.sha256(Path(pdf_path).read_bytes()).hexdigest()
    return {
        "schema_version": SCHEMA_VERSION,
        "source": {"pdf_path": str(pdf_path), "sha256": sha, "page_count": len(pages)},
        "metadata": dict(meta),
        "sections": out_sections,
        "pages": page_rows,
    }


REQUIRED_TOP = ("schema_version", "source", "metadata", "sections", "pages")
REQUIRED_META = ("title", "nct_id", "version", "date", "principal_investigator", "sponsor", "phase", "page_count")
MIN_CHARS = 1500


def validate_protocol_json(pj: dict) -> dict:
    """Deterministic JSON Validation Tool. Errors block the review; warnings are informative."""
    errors: list[str] = []
    warnings: list[str] = []
    for k in REQUIRED_TOP:
        if k not in pj:
            errors.append(f"missing top-level key '{k}'")
    if errors:
        return {"valid": False, "errors": errors, "warnings": warnings}
    meta = pj["metadata"]
    for k in REQUIRED_META:
        if k not in meta:
            errors.append(f"metadata key '{k}' missing")
    n_pages = pj["source"].get("page_count", 0)
    if n_pages < 1:
        errors.append("PDF has no pages")
    total = sum(s["char_count"] for s in pj["sections"])
    if total < MIN_CHARS:
        errors.append(f"too little extractable text ({total} chars): scanned or empty PDF")
    for s in pj["sections"]:
        if not (1 <= s["page_start"] <= s["page_end"] <= max(1, n_pages)):
            errors.append(f"section '{s.get('heading')}' has page range {s['page_start']}-{s['page_end']} outside 1-{n_pages}")
    nct = meta.get("nct_id") or ""
    if nct and not re.fullmatch(r"NCT\d{8}", nct):
        errors.append(f"malformed NCT id '{nct}'")
    content_sections = [s for s in pj["sections"] if s["index"] > 0]
    if len(content_sections) < 3:
        warnings.append(f"only {len(content_sections)} section headings detected; section attribution of findings will be coarse")
    for k in ("title", "version", "date", "principal_investigator", "sponsor"):
        if not meta.get(k):
            warnings.append(f"metadata '{k}' not found (reported by the administrative checks, never invented)")
    return {"valid": not errors, "errors": errors, "warnings": warnings}


def section_index(pj: dict) -> str:
    """Compact listing for prompts: number, title, pages."""
    rows = [f"- [{s['index']}] {s['heading']} (pp. {s['page_start']}-{s['page_end']}, {s['char_count']} chars)"
            for s in pj.get("sections", [])]
    return "\n".join(rows)


def section_for(pj: dict, page: int | None, quote: str = "") -> str:
    """Best-effort section heading for a finding: the section containing the quote,
    else the first content section on that page, else ''."""
    secs = pj.get("sections") or []
    q = " ".join((quote or "").split()).lower()
    if q and len(q) >= 12:
        mid = len(q) // 2
        windows = [w for w in (q[:80], q[max(0, mid - 40):mid + 40], q[-80:]) if len(w) >= 12]
        norm = [(s, " ".join(s["text"].split()).lower()) for s in secs]
        for w in windows:
            hits = [s for s, t in norm if w in t]
            if hits:
                return hits[0]["heading"]
    if page:
        on_page = [s for s in secs if s["page_start"] <= page <= s["page_end"]]
        if on_page:
            content = [s for s in on_page if s["index"] > 0]
            return (content or on_page)[0]["heading"]
    return ""
