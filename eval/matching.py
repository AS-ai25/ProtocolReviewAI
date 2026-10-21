"""Finding-matching rule (charter v1.4, section 2 - locked).

A predicted finding MATCHES a labeled finding when

    1. the domain is the same (administrative / scientific), and
    2. either the categories are the same or aliases of each other
       (`eval/category_aliases.json`), or the guideline reference is the same and the
       cited page is within +-1 of the labeled page.

Labels are the files in `eval/labeled_cases/*.json`; each expected finding has `domain`
and `category`, optionally `guideline_ref` and `page` (the second branch of the rule
needs both). The alias map is maintained by the team (Ron) together with the labels.

Scoring conventions shared by evaluate.py and ablation.py:

* precision of VERIFIED findings = verified predictions that match a label / verified predictions
  (the system's claims are the verified findings; unverified ones go to a human and are counted apart);
* recall (coverage) of labeled findings = labels matched by any REPORTED prediction (status
  verified or unverified) / labels. Rejected and withdrawn findings are not predictions.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ALIASES_PATH = Path(__file__).resolve().parent / "category_aliases.json"
REPORTED = ("verified", "unverified", "revise", "proposed")   # transient statuses count as unverified


def _norm(s: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", (s or "").strip().upper()).strip("_")


def load_aliases(path: Path | None = None) -> dict[str, set[str]]:
    """{canonical: {canonical, alias, ...}} - symmetric lookup built from the JSON map."""
    raw = json.loads((path or ALIASES_PATH).read_text(encoding="utf-8")) if (path or ALIASES_PATH).exists() else {}
    groups: dict[str, set[str]] = {}
    for canonical, aliases in raw.get("aliases", raw).items():
        if canonical.startswith("_"):
            continue
        group = {_norm(canonical), *(_norm(a) for a in aliases)}
        for name in group:
            groups.setdefault(name, set()).update(group)
    return groups


_ALIASES: dict[str, set[str]] | None = None


def aliases() -> dict[str, set[str]]:
    global _ALIASES
    if _ALIASES is None:
        _ALIASES = load_aliases()
    return _ALIASES


def _refs(s: str) -> set[str]:
    return set(re.findall(r"ADMIN-CHK-\d{2}|SPIRIT-\d{1,2}[a-c]?|GCP-\d{2}", (s or "").upper()))


def _pages(finding: dict) -> set[int]:
    if finding.get("page"):
        return {int(finding["page"])}
    return {int(e["page"]) for e in finding.get("evidence") or [] if e.get("page")}


def matches(pred: dict, label: dict, alias_map: dict[str, set[str]] | None = None) -> bool:
    """The locked rule: same domain AND (category alias OR same guideline_ref with page within +-1)."""
    if (pred.get("domain") or "") != (label.get("domain") or ""):
        return False
    pc, lc = _norm(pred.get("category", "")), _norm(label.get("category", ""))
    amap = alias_map if alias_map is not None else aliases()
    if pc and lc and (pc == lc or lc in amap.get(pc, set())):
        return True
    pr, lr = _refs(pred.get("guideline_ref", "")), _refs(label.get("guideline_ref", ""))
    if pr and lr and pr & lr:
        pp, lp = _pages(pred), _pages(label)
        if pp and lp and any(abs(a - b) <= 1 for a in pp for b in lp):
            return True
    return False


def score_findings(labels: list[dict], predictions: list[dict], alias_map: dict[str, set[str]] | None = None) -> dict:
    """Precision of VERIFIED findings, recall (coverage) of labels, unverified count.

    Returns the keys evaluate.py always had (tp/fp/fn/precision/recall/f1/missed/extra) plus
    `verified_precision`, `n_verified`, `n_unverified`, `matched_verified`, `coverage`.
    """
    reported = [p for p in predictions if p.get("status") in REPORTED]
    verified = [p for p in reported if p.get("status") == "verified"]
    unverified = [p for p in reported if p.get("status") != "verified"]

    label_hit = [any(matches(p, lab, alias_map) for p in reported) for lab in labels]
    pred_hit = [any(matches(p, lab, alias_map) for lab in labels) for p in reported]
    ver_hit = [any(matches(p, lab, alias_map) for lab in labels) for p in verified]

    tp = sum(label_hit)                        # labels covered by a reported finding
    fn = len(labels) - tp
    fp = sum(1 for h in pred_hit if not h)     # reported findings that match no label
    matched_pred = sum(pred_hit)
    precision = matched_pred / len(reported) if reported else (1.0 if not labels else 0.0)
    recall = tp / len(labels) if labels else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    mv = sum(ver_hit)
    verified_precision = mv / len(verified) if verified else (1.0 if not labels else 0.0)
    return {
        "tp": tp, "fp": fp, "fn": fn,
        "precision": round(precision, 3), "recall": round(recall, 3), "f1": round(f1, 3),
        "missed": sorted((lab["domain"], lab["category"]) for lab, h in zip(labels, label_hit) if not h),
        "extra": sorted({(p["domain"], p["category"]) for p, h in zip(reported, pred_hit) if not h}),
        "n_reported": len(reported), "n_verified": len(verified), "n_unverified": len(unverified),
        "matched_verified": mv, "verified_precision": round(verified_precision, 3), "coverage": round(recall, 3),
        "n_labels": len(labels),
    }
