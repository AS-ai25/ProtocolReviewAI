"""Deterministic evidence tools (v1.7). They run in code, always, for every configuration that verifies findings.

Each addresses a failure pattern seen in the 30-finding human evidence check of 4 November 2026
(reports/CP2_SUMMARY.md section 2b):

* absence_search      - "missing X" claims when X is described elsewhere in the protocol
* quote_is_mention_only - a quote that mentions the topic but shows no deficiency
* guideline_fits_category - a guideline item that does not fit the claimed category
* merge_duplicates    - the same issue reported two or three times
* numbers_table / study_design - context built once at intake for every agent
"""
from __future__ import annotations

import difflib
import re

from .checks import AGE_RES, PHASE_ALL_RE, _norm_phase, phases_mentioned, sample_sizes
from ..pdf_parser import DATE_RE, VERSION_RE

# ------------------------------------------------------------------ absence claims
ABSENCE_CATEGORIES = {
    "MISSING_SECTION", "MISSING_DOCUMENT", "METHOD_UNSPECIFIED", "SAFETY_GAP", "ETHICS_GAP", "CONSENT_GAP",
    "NO_SAMPLE_SIZE", "NO_SAMPLE_SIZE_JUSTIFICATION", "UNJUSTIFIED_SAMPLE_SIZE", "NO_STATISTICAL_PLAN", "NO_DATA_MONITORING",
    "NO_HARMS_PLAN", "NO_PRIMARY_OUTCOME", "NO_STOPPING_RULES", "RANDOMIZATION_METHOD_UNSPECIFIED", "BLINDING_UNSPECIFIED",
    "MISSING_ETHICS_STATEMENT", "MISSING_CONSENT_FORM", "MISSING_INSURANCE", "MISSING_SIGNATURE_PAGE", "MISSING_CONTACT",
}
ABSENCE_TITLE_RE = re.compile(
    r"\b(no|not|missing|absent|absence|lack(s|ing)?|without|unspecified|undefined|unclear|not\s+(specified|described|defined|"
    r"reported|provided|stated|addressed|justified|mentioned|documented)|does\s+not|fails?\s+to|omits?)\b", re.I)
NEGATION_RE = re.compile(
    r"\b(no|not|none|never|without|absent|lack(s|ing|ed)?|unspecified|undefined|unclear|unknown|to\s+be\s+(determined|defined|"
    r"decided|specified)|TBD|TBA|n/?a|not\s+applicable|pending|will\s+be\s+(determined|defined|specified)|missing|omitted)\b", re.I)

# keywords the code searches for when a finding claims that something is absent (category -> terms)
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "NO_DATA_MONITORING": ["data monitoring", "DSMB", "DMC", "safety monitoring board", "monitoring committee", "interim analysis"],
    "SAFETY_GAP": ["adverse event", "serious adverse", "SAE", "safety reporting", "harms", "pharmacovigilance", "stopping rule", "DSMB"],
    "NO_HARMS_PLAN": ["adverse event", "harms", "safety reporting", "SAE"],
    "NO_STOPPING_RULES": ["stopping rule", "withdraw", "discontinu", "interim analys", "early termination"],
    "NO_SAMPLE_SIZE": ["sample size", "participants", "patients", "n ="],
    "NO_SAMPLE_SIZE_JUSTIFICATION": ["power", "effect size", "alpha", "significance", "standard deviation", "sample size"],
    "UNJUSTIFIED_SAMPLE_SIZE": ["power", "effect size", "alpha", "standard deviation", "sample size calculation", "dropout"],
    "NO_STATISTICAL_PLAN": ["statistical analysis", "analysis plan", "statistical methods", "intention-to-treat", "per-protocol"],
    "NO_PRIMARY_OUTCOME": ["primary outcome", "primary endpoint", "primary end point"],
    "RANDOMIZATION_METHOD_UNSPECIFIED": ["randomi", "allocation", "block", "stratif", "sequence generation", "concealment"],
    "BLINDING_UNSPECIFIED": ["blind", "mask", "open-label", "open label", "placebo"],
    "CONSENT_GAP": ["informed consent", "consent form", "assent", "legally acceptable representative", "consent process"],
    "ETHICS_GAP": ["ethics committee", "IRB", "institutional review board", "Helsinki", "ethical approval", "amendment"],
    "MISSING_ETHICS_STATEMENT": ["ethics committee", "IRB", "Helsinki", "ethical approval"],
    "MISSING_CONSENT_FORM": ["informed consent", "consent form", "information sheet"],
    "MISSING_INSURANCE": ["insurance", "indemnity", "compensation", "liability"],
    "MISSING_SIGNATURE_PAGE": ["signature", "signed", "investigator agreement"],
    "MISSING_CONTACT": ["@", "tel", "phone", "contact"],
    "METHOD_UNSPECIFIED": [],     # keywords come from the title
    "MISSING_SECTION": [],
    "MISSING_DOCUMENT": ["appendix", "annex", "attached", "attachment"],
}
_STOP = {"protocol", "section", "study", "trial", "patients", "participants", "missing", "unspecified", "described", "specified",
         "defined", "reported", "provided", "stated", "without", "lacks", "lacking", "absent", "clearly", "plan", "method",
         "methods", "procedure", "details", "detail", "statement", "information", "between", "within", "should", "would",
         "which", "their", "there", "where", "these", "those", "other", "after", "before", "during", "versus", "versus"}


def is_absence_claim(finding: dict) -> bool:
    """A finding that says something is missing / not described (page 0 evidence, absence category or wording)."""
    ev = finding.get("evidence") or []
    if ev and all((e.get("page") or 0) == 0 for e in ev):
        return True
    if (finding.get("category") or "") in ABSENCE_CATEGORIES:
        return True
    return bool(ABSENCE_TITLE_RE.search(finding.get("title") or ""))


def absence_keywords(finding: dict) -> list[str]:
    """Terms to look for: the category's list, the model's own `absence_keywords` if present, and title nouns."""
    kws: list[str] = list(CATEGORY_KEYWORDS.get(finding.get("category") or "", []))
    kws += [k for k in (finding.get("absence_keywords") or []) if isinstance(k, str) and len(k) >= 3]
    for w in re.findall(r"[A-Za-z][A-Za-z\-]{4,}", finding.get("title") or ""):
        lw = w.lower()
        if lw not in _STOP and lw not in [k.lower() for k in kws]:
            kws.append(w)
    return kws[:12]


def absence_search(finding: dict, pages: list[dict], max_hits: int = 6) -> dict:
    """Where in the protocol the claimed-absent thing is mentioned. Returns {keywords, found_pages, hits}."""
    kws = absence_keywords(finding)
    hits: list[dict] = []
    for kw in kws:
        rx = re.compile(re.escape(kw), re.I)
        for p in pages:
            for m in rx.finditer(p["text"]):
                s = max(0, m.start() - 80); e = min(len(p["text"]), m.end() + 80)
                hits.append({"keyword": kw, "page": p["page"], "snippet": " ".join(p["text"][s:e].split())})
                break                                   # one hit per keyword per page is enough
    pages_found = sorted({h["page"] for h in hits})
    return {"keywords": kws, "found_pages": pages_found, "hits": hits[:max_hits]}


def quote_is_mention_only(finding: dict) -> bool:
    """An absence claim whose quote contains the topic but no negation / absence / to-be-defined wording:
    the quote shows that the topic is mentioned, not that something is missing."""
    if not is_absence_claim(finding):
        return False
    quotes = [e.get("quote") or "" for e in finding.get("evidence") or [] if (e.get("page") or 0) > 0 and e.get("quote")]
    if not quotes:
        return False
    return not any(NEGATION_RE.search(q) for q in quotes)


# ------------------------------------------------------------------ category -> guideline codes
CATEGORY_CODES: dict[str, set[str]] = {
    "REGISTRY_MISMATCH": {"SPIRIT-4", "ADMIN-CHK-03", "SPIRIT-16", "SPIRIT-19", "SPIRIT-12", "SPIRIT-15a", "SPIRIT-3b"},
    "REGISTRY_NOT_FOUND": {"SPIRIT-4", "ADMIN-CHK-03"},
    "INCONSISTENT_PHASE": {"SPIRIT-12", "SPIRIT-1a", "SPIRIT-1b", "SPIRIT-4", "ADMIN-CHK-13"},
    "INCONSISTENT_SAMPLE_SIZE": {"SPIRIT-19", "SPIRIT-4", "ADMIN-CHK-13"},
    "UNJUSTIFIED_SAMPLE_SIZE": {"SPIRIT-19"},
    "NO_SAMPLE_SIZE": {"SPIRIT-19"}, "NO_SAMPLE_SIZE_JUSTIFICATION": {"SPIRIT-19"},
    "RANDOMIZATION_METHOD_UNSPECIFIED": {"SPIRIT-21a", "SPIRIT-21b", "SPIRIT-22", "SPIRIT-23"},
    "BLINDING_UNSPECIFIED": {"SPIRIT-24a", "SPIRIT-24b", "SPIRIT-24c"},
    "NO_PRIMARY_OUTCOME": {"SPIRIT-16"},
    "NO_STATISTICAL_PLAN": {"SPIRIT-27a", "SPIRIT-27b", "SPIRIT-27c", "SPIRIT-27d", "SPIRIT-5"},
    "NO_DATA_MONITORING": {"SPIRIT-28a", "SPIRIT-28b", "SPIRIT-29"},
    "NO_HARMS_PLAN": {"SPIRIT-17", "GCP-07"},
    "NO_STOPPING_RULES": {"SPIRIT-15b", "SPIRIT-28b", "SPIRIT-25b"},
    "SAFETY_GAP": {"SPIRIT-17", "SPIRIT-28a", "SPIRIT-28b", "SPIRIT-29", "SPIRIT-15b", "GCP-07", "GCP-10", "GCP-02", "GCP-03"},
    "CONSENT_GAP": {"SPIRIT-32a", "SPIRIT-32b", "GCP-09", "ADMIN-CHK-06", "ADMIN-CHK-14"},
    "ETHICS_GAP": {"SPIRIT-30", "SPIRIT-31", "SPIRIT-33", "SPIRIT-34", "SPIRIT-7b", "GCP-01", "GCP-03", "GCP-11", "ADMIN-CHK-08"},
    "MISSING_CONSENT_FORM": {"ADMIN-CHK-06", "SPIRIT-32a", "GCP-09"},
    "MISSING_INSURANCE": {"ADMIN-CHK-07", "SPIRIT-34"},
}


def guideline_fits_category(finding: dict) -> bool | None:
    """None = no constraint for this category; otherwise whether every cited code is allowed for it."""
    allowed = CATEGORY_CODES.get(finding.get("category") or "")
    if not allowed:
        return None
    codes = re.findall(r"ADMIN-CHK-\d{2}|SPIRIT-\d{1,2}[a-dA-D]?|GCP-\d{2}", finding.get("guideline_ref") or "")
    codes = [c[:-1] + c[-1].lower() if c[-1].isalpha() else c for c in codes]
    if not codes:
        return None
    return all(c in allowed for c in codes)


# ------------------------------------------------------------------ duplicates
def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", (s or "").lower()).strip()


def _pages(f: dict) -> set[int]:
    return {e.get("page") for e in f.get("evidence") or [] if e.get("page")}


GENERIC_FOR_DUPLICATES = {"OTHER", "INTERNAL_CONTRADICTION", "METHOD_UNSPECIFIED", "FORMAT_ISSUE", "MISSING_SECTION"}


def merge_duplicates(findings: list[dict], threshold: float = 0.82) -> tuple[list[dict], list[tuple[str, str]]]:
    """Mark later LLM findings that duplicate an earlier one (same domain, same category and a shared page, or a very
    similar title) as `rejected` with a note. Nothing is removed (append-only state). Returns (findings, pairs)."""
    out, pairs = [], []
    kept: list[dict] = []
    for f in findings:
        f = dict(f)
        if f.get("source") == "llm" and f.get("status") not in ("rejected", "withdrawn"):
            dup_of = None
            for k in kept:
                if k.get("domain") != f.get("domain"):
                    continue
                sim = difflib.SequenceMatcher(None, _norm(k.get("title")), _norm(f.get("title"))).ratio()
                # same specific category on the same page with related titles, or near-identical titles
                same_cat = (k.get("category") == f.get("category") and k.get("category") not in GENERIC_FOR_DUPLICATES
                            and bool(_pages(k) & _pages(f)) and sim >= 0.55)
                if same_cat or sim >= threshold:
                    dup_of = k["id"]
                    break
            if dup_of:
                f["status"] = "rejected"
                f["critic_notes"] = f"Duplicate of {dup_of} (same issue, automatic check). " + (f.get("critic_notes") or "")
                pairs.append((f["id"], dup_of))
                out.append(f)
                continue
        kept.append(f)
        out.append(f)
    return out, pairs


# ------------------------------------------------------------------ intake context
def numbers_table(pages: list[dict]) -> dict:
    """Every number that tends to be stated inconsistently, with the pages it appears on."""
    text = "\n".join(p["text"] for p in pages)
    sizes = sample_sizes(text)

    def pages_with(rx: re.Pattern) -> list[int]:
        return [p["page"] for p in pages if rx.search(p["text"])]

    table = {
        "sample_sizes": [{"n": n, "mentions": c, "pages": pages_with(re.compile(rf"\b(?:{n}|{n:,})\b"))} for n, c in sizes.most_common(6)],
        "phases": [{"phase": ph, "pages": pages_with(re.compile(rf"\bphase\s+{re.escape(ph)}\b", re.I))} for ph in sorted(phases_mentioned(text))],
        "versions": sorted({f"v{m.group(1)} (p.{p['page']})" for p in pages for m in VERSION_RE.finditer(p["text"])})[:8],
        "dates": sorted({f"{m.group(1)} (p.{p['page']})" for p in pages[:3] for m in DATE_RE.finditer(p["text"])})[:8],
        "age_ranges": sorted({"-".join(g for g in m.groups() if g) + f" (p.{p['page']})" for p in pages for rx in AGE_RES for m in rx.finditer(p["text"])})[:8],
    }
    return table


def numbers_prompt(table: dict) -> str:
    if not table:
        return ""
    lines = ["# Numbers table (built by code at intake; use it to check internal consistency)"]
    if table.get("sample_sizes"):
        lines.append("- sample sizes: " + "; ".join(f"{x['n']} (x{x['mentions']}, pages {x['pages'][:6]})" for x in table["sample_sizes"]))
    if table.get("phases"):
        lines.append("- phases: " + "; ".join(f"phase {x['phase']} (pages {x['pages'][:6]})" for x in table["phases"]))
    for k in ("versions", "dates", "age_ranges"):
        if table.get(k):
            lines.append(f"- {k.replace('_', ' ')}: " + "; ".join(table[k]))
    return "\n".join(lines)


def study_design(pages: list[dict], registry: dict | None = None) -> dict:
    """Coarse design detection; drives which SPIRIT items are not applicable."""
    text = "\n".join(p["text"][:20000] for p in pages[:12]).lower()
    d = {
        "randomised": bool(re.search(r"\brandomi[sz]", text)) or ((registry or {}).get("raw", {}).get("protocolSection", {})
                                                                 .get("designModule", {}).get("designInfo", {}).get("allocation") == "RANDOMIZED"),
        "blinded": bool(re.search(r"\b(double|single|triple|observer)[- ]blind|\bmask(ed|ing)\b", text)),
        "open_label": bool(re.search(r"\bopen[- ]label\b", text)),
        "observational": bool(re.search(r"\bobservational\b|\bcohort study\b|\bcase[- ]control\b|\bcross[- ]sectional\b|\bregistry study\b", text)),
        "retrospective": bool(re.search(r"\bretrospective\b|\bexisting (data|records)\b|\bchart review\b|\bmedical records?\b", text)),
        "questionnaire": bool(re.search(r"\bquestionnaire\b|\bsurvey\b", text)) and not bool(re.search(r"\brandomi[sz]", text)),
        "ai_model": bool(re.search(r"\b(machine learning|deep learning|neural network|algorithm|artificial intelligence|\bAI\b|predictive model|training set|validation set)\b", text)),
        "multicentre": bool(re.search(r"\bmulti[- ]?cent(re|er)\b|\bsites?\b", text)),
    }
    na: list[str] = []
    if not d["randomised"]:
        na += ["SPIRIT-21a", "SPIRIT-21b", "SPIRIT-22", "SPIRIT-23", "SPIRIT-9b"]
    if d["open_label"] or not (d["blinded"] or d["randomised"]):
        na += ["SPIRIT-24b", "SPIRIT-24c"]
    if d["observational"] or d["retrospective"] or d["questionnaire"]:
        na += ["SPIRIT-15b", "SPIRIT-15c", "SPIRIT-15d", "SPIRIT-28a", "SPIRIT-28b", "SPIRIT-6"]
    d["non_applicable_spirit_items"] = sorted(set(na))
    kind = ("randomised trial" if d["randomised"] else "observational / registry study" if d["observational"] else
            "retrospective data study" if d["retrospective"] else "questionnaire study" if d["questionnaire"] else "interventional, non-randomised")
    if d["ai_model"]:
        kind += " with an AI / predictive-model component"
    d["kind"] = kind
    return d


def design_prompt(d: dict) -> str:
    if not d:
        return ""
    return ("# Study design detected by code (use it for applicability; do not flag non-applicable items as defects)\n"
            f"- kind: {d.get('kind')}; randomised={d.get('randomised')}, blinded={d.get('blinded')}, open_label={d.get('open_label')}, "
            f"observational={d.get('observational')}, retrospective={d.get('retrospective')}, ai_model={d.get('ai_model')}\n"
            f"- SPIRIT items that do NOT apply to this design: {', '.join(d.get('non_applicable_spirit_items') or []) or 'none'}")
