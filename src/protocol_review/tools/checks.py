"""Deterministic protocol checks.

These run in code (no LLM) and are shared by:
* the Rule-Based Baseline (`baseline.py`) - the checks ARE the baseline;
* the Administrative Review Agent, which receives their results as input and
  may add context-dependent findings on top.

Each check returns `Finding` dicts with `source="rule"` and a stable category so
the evaluation script can match them against labeled cases.
"""
from __future__ import annotations

import re
from collections import Counter

from ..state import Domain, Evidence, Finding, Severity

# ---- Required sections (ADMIN-CHK-10). code -> (label, patterns) -----------
REQUIRED_SECTIONS: dict[str, tuple[str, list[str]]] = {
    "BACKGROUND": ("Background and rationale", [r"\bbackground\b", r"\brationale\b", r"\bintroduction\b"]),
    "OBJECTIVES": ("Objectives / hypotheses", [r"\bobjectives?\b", r"\bhypothes[ie]s\b", r"\baims?\b"]),
    "DESIGN": ("Trial design", [r"\b(study|trial)\s+design\b", r"\brandomi[sz]ed\b", r"\bsingle[- ]arm\b"]),
    "ELIGIBILITY": ("Eligibility criteria", [r"\beligibility\b", r"\binclusion\s+criteria\b", r"\bexclusion\s+criteria\b"]),
    "INTERVENTIONS": ("Interventions", [r"\binterventions?\b", r"\bstudy\s+(drug|treatment|product)\b", r"\bdosing\b"]),
    "OUTCOMES": ("Outcomes / endpoints", [r"\bprimary\s+(outcome|endpoint)\b", r"\boutcome\s+measures?\b", r"\bendpoints?\b"]),
    "SAMPLE_SIZE": ("Sample size", [r"\bsample\s+size\b", r"\bpower\s+(calculation|analysis)\b", r"\bnumber\s+of\s+(participants|subjects|patients)\b"]),
    "STATISTICS": ("Statistical methods", [r"\bstatistical\s+(analysis|methods?|plan)\b", r"\banalysis\s+plan\b"]),
    "ETHICS": ("Ethics / IRB / Helsinki committee", [r"\bethic(s|al)\b", r"\bIRB\b", r"\bhelsinki\b", r"\binstitutional\s+review\s+board\b"]),
    "CONSENT": ("Informed consent", [r"\binformed\s+consent\b", r"\bconsent\s+(form|process)\b"]),
    "SAFETY": ("Adverse events / safety", [r"\badverse\s+events?\b", r"\bsafety\s+(monitoring|reporting)\b", r"\bserious\s+adverse\b", r"\bharms?\b"]),
    "DATA_MANAGEMENT": ("Data management / confidentiality", [r"\bdata\s+management\b", r"\bconfidentiality\b", r"\bdata\s+protection\b"]),
}

_NUM = r"(\d{1,3}(?:,\d{3})*|\d+)"
SAMPLE_SIZE_RES = [
    re.compile(rf"\b[nN]\s*=\s*{_NUM}\b"),
    re.compile(rf"\b{_NUM}\s+(?:participants|subjects|patients|volunteers)\b", re.I),
    re.compile(rf"\b(?:enrol+|recruit|randomi[sz]e)\w*\s+(?:a\s+total\s+of\s+|up\s+to\s+|approximately\s+)?{_NUM}\b", re.I),
    re.compile(rf"\btotal\s+(?:sample\s+size|of)\s+(?:of\s+)?{_NUM}\b", re.I),
]
AGE_RES = [
    re.compile(r"\baged?\s+(\d{1,2})\s*(?:to|-|–|and)\s*(\d{1,2})\b", re.I),
    re.compile(r"\b(\d{1,2})\s*(?:to|-|–)\s*(\d{1,2})\s+years?\s+(?:of\s+age|old)\b", re.I),
    re.compile(r"\b(?:aged?|age)\s*(?:≥|>=|at\s+least|over|above)\s*(\d{1,2})\b", re.I),
    re.compile(r"\baged?\s+(\d{1,2})\s+years?\s+(?:or|and)\s+(?:older|above|over)\b", re.I),
]
# Numbers / phases mentioned in this context describe OTHER studies, not this trial
PRIOR_STUDY_RE = re.compile(r"phase\s+(?:1|I)(?:/(?:2|II))?\s+(?:stud|trial)|previous|prior|earlier|pilot|published|literature", re.I)
PHASE_ALL_RE = re.compile(r"\bphase\s+(I{1,3}V?|IV|[1-4](?:/[1-4])?|[1-4][ab]?)\b", re.I)


def _context(text: str, start: int, end: int, before: int = 120, after: int = 40) -> str:
    """The sentence around a match (bounded by `before`/`after` chars)."""
    lo = max(0, start - before)
    chunk = text[lo:start]
    cut = max(chunk.rfind(". "), chunk.rfind("\n\n"), chunk.rfind("; "))
    if cut != -1:
        lo = lo + cut + 2
    hi = min(len(text), end + after)
    tail = text[end:hi]
    stop = tail.find(". ")
    if stop != -1:
        hi = end + stop
    return text[lo:hi]


def _norm_phase(p: str) -> str:
    p = p.upper()
    return {"I": "1", "II": "2", "III": "3", "IV": "4", "I/II": "1/2", "II/III": "2/3"}.get(p, p)


def _page_of(pages: list[dict], needle: str) -> tuple[int, str]:
    """First page containing `needle` (case-insensitive) and a short quote around it."""
    low = needle.lower()
    for p in pages:
        idx = p["text"].lower().find(low)
        if idx != -1:
            start = max(0, idx - 60)
            return p["page"], " ".join(p["text"][start:idx + len(needle) + 120].split())[:300]
    return 0, ""


def _find(pages: list[dict], pattern: str) -> tuple[int, str]:
    rx = re.compile(pattern, re.I)
    for p in pages:
        m = rx.search(p["text"])
        if m:
            start = max(0, m.start() - 60)
            return p["page"], " ".join(p["text"][start:m.end() + 120].split())[:300]
    return 0, ""


def _finding(idx: int, domain: Domain, category: str, severity: Severity, title: str, description: str,
             guideline_ref: str, evidence: list[Evidence] | None = None, recommendation: str = "") -> dict:
    prefix = "ADM" if domain == Domain.ADMINISTRATIVE else "SCI"
    return Finding(
        id=f"{prefix}-R{idx:03d}", domain=domain, category=category, severity=severity, title=title,
        description=description, evidence=evidence or [], guideline_ref=guideline_ref,
        recommendation=recommendation, source="rule",
    ).model_dump(mode="json")


# ------------------------------------------------------------ administrative
def administrative_checks(pages: list[dict], meta: dict) -> list[dict]:
    text = "\n".join(p["text"] for p in pages)
    out: list[dict] = []
    i = 0

    def add(*a, **k):
        nonlocal i
        i += 1
        out.append(_finding(i, Domain.ADMINISTRATIVE, *a, **k))

    if meta.get("likely_scanned") or meta.get("char_count", 0) < 1500:
        add("UNREADABLE_PDF", Severity.CRITICAL, "PDF text could not be extracted",
            "The document appears to be scanned or nearly empty; automated review is not possible.",
            "ADMIN-CHK-09", recommendation="Request a text-based PDF from the submitter.")
        return out  # nothing else is meaningful

    if not meta.get("title"):
        add("MISSING_TITLE", Severity.MAJOR, "No identifiable protocol title", "A descriptive title could not be found on the first pages.", "ADMIN-CHK-01")
    if not meta.get("version"):
        add("MISSING_VERSION", Severity.MAJOR, "Protocol version not stated",
            "No 'Version X.Y' identifier was found. Committees must know which version they approve.", "ADMIN-CHK-02",
            recommendation="Add version number and date to the title page and footer.")
    if not meta.get("date"):
        add("MISSING_DATE", Severity.MINOR, "Protocol date not found on the title page", "No date could be identified on the first two pages.", "ADMIN-CHK-02")
    if not meta.get("nct_id"):
        add("MISSING_REGISTRY_ID", Severity.MAJOR, "No trial registration identifier (NCT) found",
            "The protocol does not cite a ClinicalTrials.gov NCT number, so registry cross-checking is impossible.", "ADMIN-CHK-03",
            recommendation="Register the trial and cite the NCT identifier.")
    elif len(meta.get("nct_ids", [])) > 1:
        add("MULTIPLE_REGISTRY_IDS", Severity.MINOR, "Several NCT identifiers appear in the document",
            f"Found: {', '.join(meta['nct_ids'])}. Confirm which one identifies this trial.", "ADMIN-CHK-03")
    if not meta.get("principal_investigator"):
        add("MISSING_PI", Severity.MAJOR, "Principal investigator not identified", "No 'Principal Investigator: <name>' statement was found.", "ADMIN-CHK-04")
    if not meta.get("sponsor"):
        add("MISSING_SPONSOR", Severity.MAJOR, "Sponsor not identified", "No 'Sponsor: <name>' statement was found.", "ADMIN-CHK-05")

    pg, q = _find(pages, r"informed\s+consent\s+form|consent\s+form\s+(is\s+)?(attached|appended|appendix)|appendix\s+[A-Z0-9]+[^\n]{0,40}consent")
    if not pg:
        add("MISSING_CONSENT_FORM", Severity.CRITICAL, "Informed consent form not referenced or attached",
            "The submission must include the participant information sheet / informed consent form.", "ADMIN-CHK-06",
            recommendation="Attach the ICF as an appendix and reference it in the protocol.")
    pg, q = _find(pages, r"\binsurance\b|\bindemnit(y|ies)\b|\bcompensation\s+for\s+(injury|harm)\b")
    if not pg:
        add("MISSING_INSURANCE", Severity.CRITICAL, "No insurance / indemnity statement",
            "Israeli Helsinki committees require a statement on insurance or compensation for trial-related injury.", "ADMIN-CHK-07",
            recommendation="Add the insurance policy details or indemnity statement.")
    pg, q = _find(pages, r"\bhelsinki\b|\bethics\s+committee\b|\bIRB\b|\binstitutional\s+review\s+board\b")
    if not pg:
        add("MISSING_ETHICS_STATEMENT", Severity.MAJOR, "No ethics committee / Declaration of Helsinki statement",
            "The protocol should state that it will be conducted per the Declaration of Helsinki and approved by the committee.", "ADMIN-CHK-08")
    pg, q = _find(pages, r"\b(curriculum\s+vitae|CV)\b|\bsignature\s+page\b|\binvestigator\s+(agreement|signature)\b")
    if not pg:
        add("MISSING_SIGNATURE_PAGE", Severity.MINOR, "No investigator signature page or CV reference",
            "A signed investigator agreement / CV is normally part of the submission package.", "ADMIN-CHK-11")
    pg, q = _find(pages, r"[\w.+-]+@[\w-]+\.[\w.]+|\btel(ephone)?\s*[:.]|\bphone\s*[:.]")
    if not pg:
        add("MISSING_CONTACT", Severity.MINOR, "No contact details for the study team", "No email address or telephone number was found.", "ADMIN-CHK-12")

    for code, (label, patterns) in REQUIRED_SECTIONS.items():
        if not any(re.search(p, text, re.I) for p in patterns):
            add("MISSING_SECTION", Severity.MAJOR if code not in ("DATA_MANAGEMENT",) else Severity.MINOR,
                f"Missing section: {label}", f"No content matching a '{label}' section was found (code {code}).", "ADMIN-CHK-10",
                recommendation=f"Add a '{label}' section.")
    return out


# --------------------------------------------------------------- scientific
def sample_sizes(text: str) -> Counter:
    """All sample-size figures mentioned in the text -> Counter({n: mentions})."""
    found: Counter = Counter()
    for rx in SAMPLE_SIZE_RES:
        for m in rx.finditer(text):
            if PRIOR_STUDY_RE.search(_context(text, m.start(), m.end())):
                continue  # e.g. "Phase 1/2 studies (n = 600)" describes earlier work
            n = int(m.group(1).replace(",", ""))
            if 5 <= n <= 100000:
                found[n] += 1
    return found


def phases_mentioned(text: str) -> set[str]:
    """Trial phases claimed for THIS trial (ignores references to earlier studies)."""
    out: set[str] = set()
    for m in PHASE_ALL_RE.finditer(text):
        if PRIOR_STUDY_RE.search(_context(text, m.start(), m.end(), before=40, after=25)):
            continue
        out.add(_norm_phase(m.group(1)))
    return out


def scientific_checks(pages: list[dict], meta: dict) -> list[dict]:
    text = "\n".join(p["text"] for p in pages)
    out: list[dict] = []
    i = 0

    def add(*a, **k):
        nonlocal i
        i += 1
        out.append(_finding(i, Domain.SCIENTIFIC, *a, **k))

    sizes = sample_sizes(text)
    if len(sizes) > 1:
        ev = []
        for n in list(sizes)[:3]:
            pg, q = _find(pages, rf"\b(?:{n}|{n:,})\b")
            if pg:
                ev.append(Evidence(page=pg, quote=q))
        add("INCONSISTENT_SAMPLE_SIZE", Severity.MAJOR, "Sample size figures are inconsistent",
            f"Different totals appear in the document: {', '.join(str(n) for n in sizes)}. The planned sample size must be stated once and used consistently.",
            "SPIRIT-19", evidence=ev, recommendation="Reconcile the sample size across the synopsis, design and statistics sections.")
    elif not sizes:
        add("NO_SAMPLE_SIZE", Severity.MAJOR, "No explicit sample size", "No numeric sample size statement (n = ..., X participants) was found.", "SPIRIT-19")

    if not re.search(r"\bsample\s+size\b[^.]{0,300}\b(power|alpha|significance|effect\s+size|standard\s+deviation|assum)", text, re.I | re.S):
        add("NO_SAMPLE_SIZE_JUSTIFICATION", Severity.MAJOR, "Sample size not justified",
            "No power / effect-size assumptions accompany the sample size.", "SPIRIT-19",
            recommendation="State assumptions (effect size, SD, alpha, power, dropout) behind the sample size.")

    if re.search(r"\brandomi[sz]", text, re.I):
        if not re.search(r"\b(block|stratif|computer[- ]generated|random\s+number|allocation\s+(sequence|concealment)|sealed\s+envelope|central\s+randomi[sz]ation|IWRS|IVRS)\b", text, re.I):
            add("RANDOMIZATION_METHOD_UNSPECIFIED", Severity.MAJOR, "Randomisation method / allocation concealment not described",
                "The trial is randomised but the sequence generation and concealment mechanism are not specified.", "SPIRIT-21a; SPIRIT-22",
                recommendation="Describe sequence generation, allocation ratio, stratification and concealment.")
        if not re.search(r"\b(blind|mask)(ed|ing)?\b|\bopen[- ]label\b", text, re.I):
            add("BLINDING_UNSPECIFIED", Severity.MAJOR, "Blinding not addressed", "Neither blinding nor an explicit open-label design is stated.", "SPIRIT-24a")

    if not re.search(r"\bprimary\s+(outcome|endpoint)\b", text, re.I):
        add("NO_PRIMARY_OUTCOME", Severity.CRITICAL, "Primary outcome not defined", "No primary outcome / endpoint statement was found.", "SPIRIT-16")
    if not re.search(r"\bstatistical\s+(analysis|methods?|plan)\b|\banalysis\s+plan\b", text, re.I):
        add("NO_STATISTICAL_PLAN", Severity.MAJOR, "No statistical analysis plan", "The protocol lacks a statistical methods section.", "SPIRIT-27a")
    if not re.search(r"\b(data\s+(safety\s+)?monitoring\s+(board|committee)|DSMB|DMC|independent\s+data\s+monitoring)\b", text, re.I):
        add("NO_DATA_MONITORING", Severity.MINOR, "No data monitoring committee statement",
            "State whether a DMC is used and, if not, why.", "SPIRIT-28a")
    if not re.search(r"\badverse\s+events?\b|\bharms?\b|\bsafety\s+reporting\b", text, re.I):
        add("NO_HARMS_PLAN", Severity.MAJOR, "No adverse-event / harms reporting plan", "No plan for collecting and reporting harms was found.", "SPIRIT-17")
    if not re.search(r"\b(withdraw|discontinu|stopping\s+rules?|interim\s+analys)", text, re.I):
        add("NO_STOPPING_RULES", Severity.MINOR, "No discontinuation / stopping criteria", "No participant withdrawal or trial stopping rules were found.", "SPIRIT-15b")

    ages: set[tuple] = set()
    for rx in AGE_RES:
        for m in rx.finditer(text):
            ages.add(tuple(int(g) for g in m.groups() if g is not None))
    if len(ages) > 1:
        add("INCONSISTENT_AGE_RANGE", Severity.MAJOR, "Age eligibility stated inconsistently",
            f"Different age criteria appear: {sorted(ages)}.", "SPIRIT-14a",
            recommendation="Use one age range throughout the protocol.")

    phases = phases_mentioned(text)
    if len(phases) > 1:
        ev = []
        for ph in sorted(phases):
            pg, q = _find(pages, rf"\bphase\s+{ph}\b")
            if pg:
                ev.append(Evidence(page=pg, quote=q))
        add("INCONSISTENT_PHASE", Severity.MAJOR, "Trial phase stated inconsistently",
            f"The protocol describes itself as phase {' and phase '.join(sorted(phases))} in different places.", "SPIRIT-8",
            evidence=ev, recommendation="State one trial phase consistently (title, synopsis, design).")
    return out


def registry_checks(pages: list[dict], meta: dict, registry: dict | None) -> list[dict]:
    """Protocol vs ClinicalTrials.gov record comparison (deterministic part)."""
    out: list[dict] = []
    if not registry or not registry.get("found"):
        if meta.get("nct_id"):
            out.append(_finding(90, Domain.SCIENTIFIC, "REGISTRY_NOT_FOUND", Severity.MAJOR,
                                "NCT identifier not found in ClinicalTrials.gov",
                                f"{meta['nct_id']} returned no record ({(registry or {}).get('error', 'no data')}).", "ADMIN-CHK-03"))
        return out
    text = "\n".join(p["text"] for p in pages)
    i = 90
    enrol = registry.get("enrollment")
    sizes = sample_sizes(text)
    if enrol and sizes and enrol not in sizes:
        i += 1
        ev = []
        for n in list(sizes)[:2]:
            pg, q = _find(pages, rf"\b(?:{n}|{n:,})\b")
            if pg:
                ev.append(Evidence(page=pg, quote=q))
        out.append(_finding(i, Domain.SCIENTIFIC, "REGISTRY_MISMATCH", Severity.MAJOR,
                            "Enrollment differs from the registry record",
                            f"Protocol states {', '.join(map(str, sizes))} participants; ClinicalTrials.gov lists {enrol}.",
                            "SPIRIT-4", evidence=ev, recommendation="Align the protocol and the registry entry."))
    reg_phases = {_norm_phase(p.strip().replace("PHASE", "").strip()) for p in (registry.get("phase") or "").split(",") if p.strip()}
    prot_phases = phases_mentioned(text) or ({_norm_phase(meta["phase"])} if meta.get("phase") else set())
    if reg_phases and prot_phases and not (reg_phases & prot_phases):
        i += 1
        out.append(_finding(i, Domain.SCIENTIFIC, "REGISTRY_MISMATCH", Severity.MAJOR, "Trial phase differs from the registry record",
                            f"Protocol: phase {', '.join(sorted(prot_phases))}; registry: phase {', '.join(sorted(reg_phases))}.", "SPIRIT-4"))
    return out


def all_rule_checks(pages: list[dict], meta: dict, registry: dict | None = None) -> list[dict]:
    return administrative_checks(pages, meta) + scientific_checks(pages, meta) + registry_checks(pages, meta, registry)
