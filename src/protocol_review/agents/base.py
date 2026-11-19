"""Helpers shared by all agents."""
from __future__ import annotations

import difflib
import json
import re

from ..knowledge_base import rule_codes
from ..protocol_json import section_for, section_index
from ..state import FindingStatus, ReviewState
from ..tools import evidence_tools

MAX_PROTOCOL_CHARS = 400_000  # ~100k tokens; protocols are normally far smaller


PROTOCOL_START = "<<<PROTOCOL DOCUMENT START>>>"
PROTOCOL_END = "<<<PROTOCOL DOCUMENT END>>>"


def protocol_text(state: ReviewState) -> str:
    """The protocol text between two marker lines (prompt hardening, 19 November 2026): the system prompts tell the
    agents that everything between the markers is data. A document cannot close the block itself: a marker that appears
    inside the protocol text is defused in the prompt copy (the pages used for the evidence check are untouched)."""
    text = state.get("pdf_text") or ""
    if len(text) > MAX_PROTOCOL_CHARS:
        text = text[:MAX_PROTOCOL_CHARS] + f"\n\n[TRUNCATED: {len(text) - MAX_PROTOCOL_CHARS} characters omitted]"
    text = text.replace("<<<PROTOCOL DOCUMENT", "<protocol document")
    return f"{PROTOCOL_START}\n{text}\n{PROTOCOL_END}"


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
    # sub-item letters are lower-case in the knowledge base (SPIRIT-27b); the upper-case-only class used until
    # 2026-11-04 cut "SPIRIT-27b" to "SPIRIT-27", an unknown code, and demoted such findings to unverified
    ref_codes = [c[:-1] + c[-1].lower() if c[-1].isalpha() else c        # the KB spells sub-items in lower case
                 for c in re.findall(r"ADMIN-CHK-\d{2}|SPIRIT-\d{1,2}[a-dA-D]?|GCP-\d{2}", ref)]
    ref_ok = bool(ref_codes) and all(c in codes for c in ref_codes)
    absence_claim = not ev or all((e.get("page") or 0) == 0 for e in ev)
    # v1.7 code evidence tools: does the protocol mention the thing claimed absent? does the quote show a deficiency
    # or only the topic? does the cited guideline item fit the category?
    claims_absence = evidence_tools.is_absence_claim(finding)
    search = evidence_tools.absence_search(finding, pages) if claims_absence else {"keywords": [], "found_pages": [], "hits": []}
    return {
        "finding_id": finding.get("id"),
        "evidence_checked": len(ev),
        "evidence_found": sum(1 for r in results if r["found"]),
        "evidence_details": results,
        "guideline_ref_valid": ref_ok,
        "absence_claim": absence_claim,  # finding says something is missing -> no quote expected
        "claims_absence": claims_absence,
        "absence_search_keywords": search["keywords"],
        "absence_search_pages": search["found_pages"],      # pages where the supposedly absent topic is described
        "absence_search_hits": search["hits"][:4],
        "quote_mention_only": evidence_tools.quote_is_mention_only(finding),
        "guideline_fits_category": evidence_tools.guideline_fits_category(finding),
    }


def code_status(v: dict) -> tuple[FindingStatus | None, str]:
    """The deterministic floor (v1.7): the reasons for which a finding can never be `verified`, whatever an agent says.
    Returns (UNVERIFIED, note) or (None, "")."""
    if v.get("evidence_checked") and v.get("evidence_found", 0) < v.get("evidence_checked", 0):
        return FindingStatus.UNVERIFIED, "Evidence quote not located in the protocol (automatic check); human review required."
    if not v.get("guideline_ref_valid"):
        return FindingStatus.UNVERIFIED, "Guideline code missing or unknown (automatic check); human review required."
    if v.get("claims_absence") and v.get("absence_search_pages"):
        return FindingStatus.UNVERIFIED, (f"Claims something is missing, but the topic is described on page(s) "
                                          f"{v['absence_search_pages'][:6]} (automatic absence search); human review required.")
    if v.get("quote_mention_only"):
        return FindingStatus.UNVERIFIED, ("The quote mentions the topic but shows no deficiency (automatic check: a mention is not "
                                          "evidence of absence); human review required.")
    if v.get("guideline_fits_category") is False:
        return FindingStatus.UNVERIFIED, "The cited guideline item does not fit the finding's category (automatic check); human review required."
    return None, ""


def auto_status_from_verification(v: dict) -> FindingStatus | None:
    """Rule findings are verified by construction; LLM findings whose quotes all
    check out AND cite a valid KB code may be auto-verified at the admin stage
    (no admin critic in this architecture)."""
    if v["guideline_ref_valid"] and v["evidence_checked"] and v["evidence_found"] == v["evidence_checked"] and code_status(v)[0] is None:
        return FindingStatus.VERIFIED
    return None


def context_block(state: ReviewState) -> str:
    """v1.7 intake context for the LLM agents: the numbers table and the detected design."""
    parts = [evidence_tools.design_prompt(state.get("study_design") or {}), evidence_tools.numbers_prompt(state.get("numbers_table") or {})]
    return "\n\n".join(p for p in parts if p)
