"""Draw the sheet of VERIFIED findings that match no blind label, for the labeler to classify (mentor finding M5).

    python eval/make_unmatched_check.py                                  (row agents_full of the latest live run)
    python eval/make_unmatched_check.py --stamp 20261029-205913 --n 40 --seed 20261110

The mentor's question (8 Nov 2026): "77% of the verified findings match no label - are they wrong?". Label-matching
precision cannot answer it: a verified finding that matches no label may be right and unlabeled, a duplicate of a
finding that did match, wrong, or undecidable from its evidence. The labeler classifies a stratified sample into exactly
those four classes.

Takes the scientific findings of one ablation row with status `verified` that match none of the case's labels
(`eval/matching.py`, the locked rule), keeps those that cite a passage, and samples `n` of them with as equal a share per
case as the counts allow (deterministic seed). Writes two files next to each other:

    <out>                       the sheet to fill: one row per sampled finding, last three columns empty
    <out stem>_reference.csv    every VERIFIED scientific finding of the same runs that DID match a label, with the
                                label it matched, so "duplicate of a matched finding" can be checked by id
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "eval"))

from matching import aliases, matches  # noqa: E402
from protocol_review.config import settings  # noqa: E402

RESULTS = ROOT / "eval" / "results"
CASES = ROOT / "eval" / "labeled_cases"
OUT = ROOT / "eval" / "human_check" / "unmatched_verified_check.csv"
CLASSES = "true but unlabeled / duplicate of a matched finding / wrong / cannot tell"
HEADER = ["run_id", "finding_id", "case_id", "source", "category", "severity", "guideline_ref", "page", "quote", "title",
          "description", f"classification ({CLASSES})", "duplicate_of (finding_id from the reference sheet)", "comment"]
REF_HEADER = ["run_id", "finding_id", "case_id", "category", "guideline_ref", "page", "title", "matched_label_id", "matched_label_category", "matched_label_page"]


def latest_stamp() -> str:
    runs = sorted(p for p in RESULTS.glob("ablation-*.json") if "nollm" not in p.name)
    if not runs:
        raise SystemExit("no live ablation run in eval/results/")
    return runs[-1].stem.replace("ablation-", "")


def _labels(case_id: str) -> list[dict]:
    f = CASES / f"{case_id}.json"
    if not f.exists():
        raise SystemExit(f"missing labeled case {f}")
    data = json.loads(f.read_text(encoding="utf-8"))
    labs = [dict(x) for x in data["expected_findings"] if x.get("domain") == "scientific"]
    for i, x in enumerate(labs, 1):
        x.setdefault("id", f"LABEL-{i:02d}")
    return labs


def split(stamp: str, row_key: str, outputs: Path | None = None) -> tuple[dict[str, list[dict]], list[dict]]:
    """Per case: verified scientific findings that match no label; plus the matched ones (reference)."""
    outputs = outputs or settings.output_path
    summary = json.loads((RESULTS / f"ablation-{stamp}.json").read_text(encoding="utf-8"))
    row = next((r for r in summary["rows"] if r["key"] == row_key), None)
    if row is None:
        raise SystemExit(f"row {row_key} not in ablation-{stamp}.json")
    am = aliases()
    unmatched: dict[str, list[dict]] = {}
    reference: list[dict] = []
    for pc in row["per_case"]:
        case_id = pc["case"]
        run_id = f"abl-{row_key}-{case_id}-{stamp}"
        f = outputs / run_id / "findings.json"
        if not f.exists():
            print(f"skip {case_id}: {f} missing")
            continue
        labels = _labels(case_id)
        rows = []
        for x in json.loads(f.read_text(encoding="utf-8")):
            if x.get("status") != "verified" or x.get("domain") != "scientific":
                continue
            ev = [e for e in x.get("evidence") or [] if e.get("page") and e.get("quote")]
            hit = next((lab for lab in labels if matches(x, lab, am)), None)
            if hit is not None:
                reference.append({"run_id": run_id, "finding_id": x["id"], "case_id": case_id, "category": x.get("category", ""),
                                  "guideline_ref": x.get("guideline_ref", ""), "page": ev[0]["page"] if ev else "",
                                  "title": x.get("title", ""), "matched_label_id": hit["id"],
                                  "matched_label_category": hit.get("category", ""), "matched_label_page": hit.get("page", "")})
                continue
            if not ev:
                continue
            rows.append({"run_id": run_id, "finding_id": x["id"], "case_id": case_id, "source": x.get("source", ""),
                         "category": x.get("category", ""), "severity": x.get("severity", ""), "guideline_ref": x.get("guideline_ref", ""),
                         "page": ev[0]["page"], "quote": ev[0]["quote"].replace("\n", " ").strip(),
                         "title": x.get("title", ""), "description": (x.get("description") or "").replace("\n", " ").strip()})
        unmatched[case_id] = rows
    return unmatched, reference


def sample(cands: dict[str, list[dict]], n: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    pools = {k: v[:] for k, v in cands.items() if v}
    for v in pools.values():
        rng.shuffle(v)
    picked: list[dict] = []
    while len(picked) < n and any(pools.values()):   # round robin: one per case per pass
        for k in sorted(pools):
            if pools[k] and len(picked) < n:
                picked.append(pools[k].pop())
    return sorted(picked, key=lambda r: (r["case_id"], r["finding_id"]))


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stamp", default=None, help="ablation run stamp (default: latest live run)")
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--seed", type=int, default=20261110)
    ap.add_argument("--row", default="agents_full")
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--outputs", default=None, help="folder holding the abl-* run directories (default: settings.output_path)")
    a = ap.parse_args(argv)
    stamp = a.stamp or latest_stamp()
    unmatched, reference = split(stamp, a.row, Path(a.outputs) if a.outputs else None)
    total = sum(len(v) for v in unmatched.values())
    rows = sample(unmatched, a.n, a.seed)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(HEADER)
        for r in rows:
            w.writerow([r[k] for k in HEADER[:11]] + ["", "", ""])
    ref = out.with_name(out.stem + "_reference.csv")
    with ref.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(REF_HEADER)
        for r in sorted(reference, key=lambda r: (r["case_id"], r["finding_id"])):
            w.writerow([r[k] for k in REF_HEADER])
    print(f"run {stamp}, row {a.row}: {total} verified scientific findings match no label across {len(unmatched)} cases "
          f"({', '.join(f'{k}={len(v)}' for k, v in sorted(unmatched.items()))}); sampled {len(rows)} -> {out}; "
          f"{len(reference)} matched findings -> {ref}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
