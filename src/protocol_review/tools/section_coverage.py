"""Advisory, deterministic screening for scientific protocol section coverage.
No absence claims, no auto-verified findings, no impact on scores or baseline metrics.
"""
from __future__ import annotations
import re

# These are screening groups, NOT a complete reproduction of SPIRIT 2025.
# Official SPIRIT 2025 item identifiers are specified separately in KB.
SECTION_GROUPS = {
    "background": ("Background and rationale", [r"background", r"introduction", r"rationale"], "9a"),
    "objectives": ("Objectives / hypotheses", [r"objectives?", r"hypothes[ei]s", r"study aims?"], "10"),
    "design": ("Trial design", [r"study design", r"trial design", r"design and methods"], "12"),
    "inclusion": ("Inclusion criteria", [r"inclusion criteria", r"inclusion requirements", r"eligible participants"], "14a"),
    "exclusion": ("Exclusion criteria", [r"exclusion criteria", r"exclusion requirements", r"ineligible participants"], "14a"),
    "interventions": ("Intervention and comparator", [r"study interventions?", r"treatment arms?", r"study treatment", r"intervention and comparator"], "15a"),
    "outcomes": ("Outcome measures / endpoints", [r"outcome measures?", r"primary endpoints?", r"primary outcomes?", r"study endpoints?"], "16"),
    "harms": ("Harms / safety monitoring", [r"safety monitoring", r"adverse events?", r"safety assessments?", r"risk management"], "17"),
    "timeline": ("Participant timeline", [r"schedule of (?:events|assessments|activities)", r"study schedule", r"visit schedule", r"participant timeline"], "18"),
    "sample_size": ("Sample size justification", [r"sample size", r"power calculation", r"power analysis"], "19"),
    "randomization": ("Randomisation methods", [r"randomi[sz]ation", r"randomi[sz]ation procedure", r"random allocation"], "21a"),
    "blinding": ("Blinding / masking", [r"blinding", r"masking", r"open.label"], "24a"),
    "data": ("Data management", [r"data management", r"data security", r"data handling"], "26"),
    "statistics": ("Statistical methods", [r"statistical analysis", r"statistical methods", r"statistical considerations"], "27a"),
    "ethics": ("Ethics and approval", [r"ethics approval", r"ethical considerations", r"institutional review board", r"research ethics committee"], "30"),
    "consent": ("Informed consent process", [r"informed consent", r"consent procedure", r"consent process"], "32a"),
}


def coverage_screen(pages: list[dict], *, randomized: bool | None = None) -> list[dict]:
    """Return section signals from paragraph-like headings, never definitive omissions.

    randomized=None means applicability has not been established. A negative signal
    must be reviewed in context (abbreviations, tables, embedded images, annexes).
    """
    found=[]
    for key,(label,patterns,spirit_item) in SECTION_GROUPS.items():
        applicable = not (randomized is False and key in {'randomization','blinding'})
        if not applicable:
            found.append(dict(key=key,label=label,spirit_2025_item=spirit_item,status='not_applicable',page=None))
            continue
        heading_page=None
        mention_page=None
        for p in pages:
            number=p.get('page')
            content=p.get('text','')
            for line in content.splitlines():
                line=line.strip()
                # Heading-like only: short line, optional numeric prefix, no full sentence.
                candidate=re.sub(r'^\d+(?:\.\d+)*[.)]?\s+', '', line)
                if 3<=len(candidate)<=95 and len(candidate.split())<=11:
                    if any(re.search(r'(?i)\b(?:'+pattern+r')\b', candidate) for pattern in patterns):
                        heading_page=number
                        break
            if heading_page is not None:break
            if mention_page is None and any(re.search(r'(?i)\b(?:'+pattern+r')\b',content) for pattern in patterns):
                mention_page=number
        status='heading_detected' if heading_page is not None else ('mentioned_only' if mention_page is not None else 'needs_manual_review')
        found.append(dict(key=key,label=label,spirit_2025_item=spirit_item,status=status,page=heading_page if heading_page is not None else mention_page))
    return found


def coverage_prompt(pages: list[dict]) -> str:
    """Support scientific review without modifying verification/scoring or ablation comparability."""
    report=coverage_screen(pages)
    rows=[f"- {x['label']} (SPIRIT 2025 {x['spirit_2025_item']}): {x['status']}" + (f", possible page {x['page']}" if x['page'] is not None else '') for x in report]
    return ("# Advisory scientific section-coverage screen (NOT verified findings)\n"
        "Check these signals against the FULL protocol and trial type. Missing headings alone are NOT proof of missing content. "
        "Distinguish absent content from differently named, embedded or not-applicable content; "
        "check inclusion AND exclusion separately. For missing material request human review; "
        "do not invent evidence, do not automatically assign MAJOR_CONCERNS.\n" + "\n".join(rows))


def spirit_2025_catalog_screen(pages: list[dict], *, randomized: bool | None = None) -> list[dict]:
    """Complete item-level advisory inventory, NOT automatic compliance classification.

    All official subitems are represented. Only 16 section families have heading heuristics;
    the rest need contextual model/human assessment. No invented absent findings.
    """
    import json
    from pathlib import Path
    catalog_path = Path(__file__).resolve().parents[3] / "knowledge_base" / "scientific" / "spirit_2025_items.json"
    if not catalog_path.is_file():
        return []  # installed without repository KB: prompt still loads markdown catalog
    catalog=json.loads(catalog_path.read_text(encoding="utf-8"))["items"]
    section_signal=coverage_screen(pages,randomized=randomized)
    by_code={s["spirit_2025_item"]:s for s in section_signal}
    result=[]
    for item in catalog:
        status="needs_context_review"
        if randomized is False:
            status="outside_spirit_2025_primary_scope"
        elif item["id"] in {"24b","24c","14b","32b","15c"}:
            status="conditional_applicability_review"
        elif item["id"] in by_code:
            status=by_code[item["id"]]["status"]
        result.append({"code":item["code"],"topic":item["topic"],"status":status})
    return result
