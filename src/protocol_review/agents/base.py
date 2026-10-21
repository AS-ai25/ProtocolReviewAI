"""Helpers shared by all agents."""
from __future__ import annotations

import difflib
import json
import re

from ..knowledge_base import rule_codes
from ..protocol_json import section_for, section_index
from ..state import FindingStatus, ReviewState

MAX_PROTOCOL_CHARS = 400_000  # ~100k tokens; protocols are normally far smaller


def protocol_text(state: ReviewState) -> str:
    text = state.get("pdf_text") or ""
    if len(text) > MAX_PROTOCOL_CHARS:
        return text[:MAX_PROTOCOL_CHARS] + f"\n\n[TRUNCATED: {len(text) - MAX_PROTOCOL_CHARS} characters omitted]"
    return text


def findings_json(findings: list[dict]) -> str:
    slim = [{k: v for k, v in f.items() if k in (
        "id", "domain", "category", "severity", "title", "description", "evidence", "guideline_ref",
        "recommendation", "status", "critic_notes", "source")} for f in findings]
    return json.dumps(slim, indent=1, ensure_ascii=False)


def renumber(findings: list[dict], prefix: str, previous: list[dict] | None = None) -> list[dict]:
    """Give LLM findings stable ids (ADM-L001...) so they never clash with rule ids.

    In a revision round `previous` holds the earlier LLM findings: an emitted finding
    keeps its id when it re-uses a previous id or title; new ones get the next free number.
    """
    prev_by_id = {f["id"]: f for f in previous or []}
    prev_by_title = {_norm(f.get("title", "")): f["id"] for f in previous or []}
    used: set[str] = set()
    next_n = 1 + max([int(i.split("-L")[1]) for i in prev_by_id if "-L" in i] or [0])
    out = []
    for f in findings:
        f = dict(f)
        fid = f.get("id", "")
        title_key = _norm(f.get("title", ""))
        if fid in prev_by_id and fid not in used:
            pass
        elif prev_by_title.get(title_key) and prev_by_title[title_key] not in used:
            fid = prev_by_title[title_key]
        else:
            fid = f"{prefix}-L{next_n:03d}"
            next_n += 1
        used.add(fid)
        f["id"] = fid
        out.append(f)
    return out


def withdraw_missing(previous: list[dict], current: list[dict]) -> list[dict]:
    """Append-only state: findings the reviewer did not re-emit are kept as WITHDRAWN."""
    kept = {f["id"] for f in current}
    out = []
    for f in previous:
        if f["id"] not in kept and f["status"] != FindingStatus.WITHDRAWN.value:
            f = dict(f)
            f["status"] = FindingStatus.WITHDRAWN.value
            f["critic_notes"] = (f.get("critic_notes") or "") + " [withdrawn by the reviewer in the revision round]"
            out.append(f)
    return out


def attach_sections(findings: list[dict], protocol_json: dict) -> list[dict]:
    """Fill `section` from the protocol JSON when the agent left it empty (in place)."""
    for f in findings:
        if f.get("section"):
            continue
        ev = f.get("evidence") or []
        page = next((e.get("page") for e in ev if e.get("page")), None)
        quote = next((e.get("quote") for e in ev if e.get("quote")), "")
        f["section"] = section_for(protocol_json, page, quote)
    return findings


def sections_block(state: ReviewState) -> str:
    pj = state.get("protocol_json") or {}
    if not pj.get("sections"):
        return ""
    return "# Protocol sections (index, heading, pages) - use the heading in `section`\n" + section_index(pj)


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip().lower()


def quote_in_pages(quote: str, pages: list[dict], page: int | None = None, threshold: float = 0.8) -> tuple[bool, int]:
    """Does `quote` appear (fuzzily) in the protocol? Returns (found, page_found)."""
    q = _norm(quote)
    if len(q) < 12:
        return False, 0
    candidates = [p for p in pages if not page or p["page"] == page] or pages
    for p in candidates + [p for p in pages if p not in candidates]:
        t = _norm(p["text"])
        if q in t:
            return True, p["page"]
        # fuzzy: best matching window of the same length
        if len(t) > len(q):
            sm = difflib.SequenceMatcher(None, q, t, autojunk=False)
            m = sm.find_longest_match(0, len(q), 0, len(t))
            if m.size / max(1, len(q)) >= threshold:
                return True, p["page"]
    return False, 0


def verify_evidence(finding: dict, pages: list[dict], codes: set[str] | None = None) -> dict:
    """Deterministic checks the critic (and admin stage) run before any LLM judgement."""
    codes = codes if codes is not None else rule_codes()
    ev = finding.get("evidence") or []
    results = []
    for e in ev:
        ok, pg = quote_in_pages(e.get("quote", ""), pages, e.get("page") or None)
        results.append({"page": e.get("page"), "found": ok, "found_on_page": pg})
    ref = (finding.get("guideline_ref") or "").strip()
    ref_codes = re.findall(r"ADMIN-CHK-\d{2}|SPIRIT-\d{1,2}[A-D]?|GCP-\d{2}", ref)
    ref_ok = bool(ref_codes) and all(c in codes for c in ref_codes)
    absence_claim = not ev or all((e.get("page") or 0) == 0 for e in ev)
    return {
        "finding_id": finding.get("id"),
        "evidence_checked": len(ev),
        "evidence_found": sum(1 for r in results if r["found"]),
        "evidence_details": results,
        "guideline_ref_valid": ref_ok,
        "absence_claim": absence_claim,  # finding says something is missing -> no quote expected
    }


def auto_status_from_verification(v: dict) -> FindingStatus | None:
    """Rule findings are verified by construction; LLM findings whose quotes all
    check out AND cite a valid KB code may be auto-verified at the admin stage
    (no admin critic in this architecture)."""
    if v["guideline_ref_valid"] and v["evidence_checked"] and v["evidence_found"] == v["evidence_checked"]:
        return FindingStatus.VERIFIED
    return None
