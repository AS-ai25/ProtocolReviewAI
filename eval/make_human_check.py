"""Draw the 30-finding human-check sheet from a live ablation run (charter v1.4 section 2, open decision 6).

    python eval/make_human_check.py                       (latest eval/results/ablation-<stamp>.json)
    python eval/make_human_check.py --stamp 20261029-183012 --n 30 --seed 20261030

Takes the VERIFIED findings of the full system (ablation row `agents_full`) on every case of that run, keeps those
that cite a passage (page > 0 and a quote), and samples `n` of them stratified across the cases (as equal a share
per case as the counts allow, deterministic seed). Writes `eval/human_check/verified_findings_check.csv` with the
columns the labeling guide defines; the labeler fills the last two WITHOUT reading the finding's explanation,
looking only at the PDF page: does the quoted passage on that page show the problem the finding names?
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

from protocol_review.config import settings  # noqa: E402

RESULTS = ROOT / "eval" / "results"
OUT = ROOT / "eval" / "human_check" / "verified_findings_check.csv"
HEADER = ["run_id", "finding_id", "case_id", "page", "quote", "guideline_ref", "supports (yes / partly / no)", "comment"]


def latest_stamp() -> str:
    runs = sorted(p for p in RESULTS.glob("ablation-*.json") if "nollm" not in p.name)
    if not runs:
        raise SystemExit("no live ablation run in eval/results/")
    return runs[-1].stem.replace("ablation-", "")


def candidates(stamp: str, row_key: str = "agents_full", outputs: Path | None = None) -> dict[str, list[dict]]:
    outputs = outputs or settings.output_path
    summary = json.loads((RESULTS / f"ablation-{stamp}.json").read_text(encoding="utf-8"))
    row = next((r for r in summary["rows"] if r["key"] == row_key), None)
    if row is None:
        raise SystemExit(f"row {row_key} not in ablation-{stamp}.json")
    out: dict[str, list[dict]] = {}
    for pc in row["per_case"]:
        run_id = f"abl-{row_key}-{pc['case']}-{stamp}"
        f = outputs / run_id / "findings.json"
        if not f.exists():
            print(f"skip {pc['case']}: {f} missing")
            continue
        rows = []
        for x in json.loads(f.read_text(encoding="utf-8")):
            if x.get("status") != "verified":
                continue
            ev = [e for e in x.get("evidence") or [] if e.get("page") and e.get("quote")]
            if not ev:
                continue
            rows.append({"run_id": run_id, "finding_id": x["id"], "case_id": pc["case"], "page": ev[0]["page"],
                         "quote": ev[0]["quote"].replace("\n", " ").strip(), "guideline_ref": x.get("guideline_ref", ""),
                         "category": x.get("category", ""), "source": x.get("source", "")})
        out[pc["case"]] = rows
    return out


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
    if hasattr(sys.stdout, "reconfigure"):      # Windows consoles default to cp1252
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stamp", default=None, help="ablation run stamp (default: latest live run)")
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--seed", type=int, default=20261030)
    ap.add_argument("--row", default="agents_full")
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--outputs", default=None, help="folder holding the abl-* run directories (default: settings.output_path)")
    a = ap.parse_args(argv)
    stamp = a.stamp or latest_stamp()
    cands = candidates(stamp, a.row, Path(a.outputs) if a.outputs else None)
    total = sum(len(v) for v in cands.values())
    rows = sample(cands, a.n, a.seed)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(HEADER)
        for r in rows:
            w.writerow([r["run_id"], r["finding_id"], r["case_id"], r["page"], r["quote"], r["guideline_ref"], "", ""])
    print(f"run {stamp}, row {a.row}: {total} verified findings with a cited passage across {len(cands)} cases "
          f"({', '.join(f'{k}={len(v)}' for k, v in sorted(cands.items()))}); sampled {len(rows)} -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
