"""Re-score a finished live ablation run from its saved findings - no LLM calls.

    python eval/rescore.py                       (latest live run in eval/results/, labels in eval/labeled_cases/)
    python eval/rescore.py --stamp 20261029-205913 --out reports/results.md

`eval/ablation.py` stores every configuration's findings per case under `outputs/abl-<config>-<case>-<stamp>/`
(`findings.json` for the agent configurations, `single_agent_findings.json` for the single agent) and the cost /
runtime per case in `eval/results/ablation-<stamp>.json`. Scoring is a pure function of those findings and the
label files, so when a label file is corrected (for example the domain of a finding) the table is rebuilt from
the saved outputs instead of re-running the models. The header of the generated report says so.

The report carries the charter table (all findings vs all labels) and two additional views:

* **scientific domain only** - labels and predictions restricted to `domain == scientific`. This is the view the
  reduced-scope plan asks for ("labels for the scientific part only where the administrative documents are
  absent"): public registry protocols carry no consent form, insurance statement or signature page, and the
  labeler deliberately did not record those absences, so the administrative package-completeness findings are
  true but outside the label scope.
* **critic contribution** - for the full system, what the Scientific Critic did with the reviewer's findings
  (verified / unverified / rejected / withdrawn / severity changes) and how the matched share differs between
  verified and unverified findings.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "eval"))

from ablation import CONFIGS, load_cases, render_markdown  # noqa: E402
from matching import score_findings  # noqa: E402
from protocol_review.config import settings  # noqa: E402

RESULTS = ROOT / "eval" / "results"
OUTPUTS = settings.output_path   # overridable with --outputs (the tests redirect OUTPUT_DIR to a temp folder)


def latest_stamp() -> str:
    runs = sorted(p for p in RESULTS.glob("ablation-*.json") if "nollm" not in p.name)
    if not runs:
        raise SystemExit("no live ablation run in eval/results/")
    return runs[-1].stem.replace("ablation-", "")


def saved_findings(cfg: dict, case_id: str, stamp: str, outputs: Path | None = None) -> list[dict]:
    d = (outputs or OUTPUTS) / f"abl-{cfg['key']}-{case_id}-{stamp}"
    f = d / ("single_agent_findings.json" if cfg["kind"] == "single" else "findings.json")
    if not f.exists():
        raise SystemExit(f"missing {f}")
    return json.loads(f.read_text(encoding="utf-8"))


def rescore(summary: dict, cases: list[dict], stamp: str, *, domain: str | None = None,
            outputs: Path | None = None) -> list[dict]:
    """Rebuild the ablation rows from the saved findings; `domain` restricts labels and predictions."""
    cost_by = {(r["key"], pc["case"]): pc for r in summary["rows"] for pc in r["per_case"]}
    rows = []
    for cfg in CONFIGS:
        if cfg["key"] not in {r["key"] for r in summary["rows"]}:
            continue
        per_case, totals = [], {"labels": 0, "tp": 0, "n_verified": 0, "matched_verified": 0, "n_unverified": 0,
                                "llm_calls": 0, "input_tokens": 0, "output_tokens": 0, "runtime_s": 0.0}
        for c in cases:
            preds = saved_findings(cfg, c["case_id"], stamp, outputs)
            labels = c["expected_findings"]
            if domain:
                preds = [p for p in preds if p.get("domain") == domain]
                labels = [x for x in labels if x.get("domain") == domain]
            s = score_findings(labels, preds)
            old = cost_by[(cfg["key"], c["case_id"])]
            row = {"case": c["case_id"], "decision": old["decision"], "expected_decision": old["expected_decision"],
                   "runtime_s": old["runtime_s"], "n_findings": len(preds), "llm_calls": old["llm_calls"],
                   "input_tokens": old["input_tokens"], "output_tokens": old["output_tokens"], **s}
            per_case.append(row)
            totals["labels"] += s["n_labels"]; totals["tp"] += s["tp"]
            totals["n_verified"] += s["n_verified"]; totals["matched_verified"] += s["matched_verified"]
            totals["n_unverified"] += s["n_unverified"]
            totals["llm_calls"] += row["llm_calls"]; totals["input_tokens"] += row["input_tokens"]
            totals["output_tokens"] += row["output_tokens"]; totals["runtime_s"] += row["runtime_s"]
        vp = totals["matched_verified"] / totals["n_verified"] if totals["n_verified"] else 0.0
        cov = totals["tp"] / totals["labels"] if totals["labels"] else 1.0
        rows.append({"key": cfg["key"], "label": cfg["label"], "kind": cfg["kind"], "kwargs": cfg["kwargs"],
                     "verified_precision": round(vp, 3), "coverage": round(cov, 3),
                     **{k: (round(v, 1) if isinstance(v, float) else v) for k, v in totals.items()}, "per_case": per_case})
    return rows


def _pct(x: float) -> str:
    return f"{100 * x:.0f}%"


def view_table(rows: list[dict], title: str, intro: str) -> list[str]:
    md = [f"## {title}", "", intro, "",
          "| # | Configuration | Precision of VERIFIED findings | Recall (coverage) of labeled findings | Unverified |",
          "|---|---|---|---|---|"]
    for i, r in enumerate(rows, 1):
        md.append(f"| {i} | {r['label']} | {_pct(r['verified_precision'])} ({r['matched_verified']}/{r['n_verified']}) | "
                  f"{_pct(r['coverage'])} ({r['tp']}/{r['labels']}) | {r['n_unverified']} |")
    md += ["", "| Configuration | Case | Verified | Matched verified | Unverified | Coverage | Missed labels |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        for c in r["per_case"]:
            md.append(f"| {r['label']} | {c['case']} | {c['n_verified']} | {c['matched_verified']} | {c['n_unverified']} | "
                      f"{c['tp']}/{c['n_labels']} | {', '.join(x[1] for x in c['missed']) or '-'} |")
    return md + [""]


def critic_section(cases: list[dict], stamp: str, outputs: Path | None = None) -> list[str]:
    full = next(c for c in CONFIGS if c["key"] == "agents_full")
    no_critic = next(c for c in CONFIGS if c["key"] == "agents_no_critic")
    md = ["## Critic contribution (full system, scientific findings)", "",
          "What the Scientific Critic did with the reviewer's findings, per protocol. `matched` = the finding matches a "
          "blind label. A critic that works should leave a higher matched share among the findings it verified than among "
          "those it sent to a human (unverified) or rejected.", "",
          "| Case | Reviewer findings (no-critic run) | Full run: verified (matched) | unverified (matched) | rejected / withdrawn (matched) | critic-raised issues |",
          "|---|---|---|---|---|---|"]
    tot = collections.Counter()
    for c in cases:
        labels = [x for x in c["expected_findings"] if x["domain"] == "scientific"]
        base = [p for p in saved_findings(no_critic, c["case_id"], stamp, outputs) if p["domain"] == "scientific"]
        preds = [p for p in saved_findings(full, c["case_id"], stamp, outputs) if p["domain"] == "scientific"]

        def bucket(status_set):
            sel = [p for p in preds if p["status"] in status_set and not p["id"].startswith("SCI-C")]
            m = sum(1 for p in sel if score_findings(labels, [p])["matched_verified" if p["status"] == "verified" else "tp"])
            return len(sel), m
        v, vm = bucket({"verified"})
        u, um = bucket({"unverified", "revise", "proposed"})
        r, rm = bucket({"rejected", "withdrawn"})
        raised = sum(1 for p in preds if p["id"].startswith("SCI-C"))
        tot.update({"v": v, "vm": vm, "u": u, "um": um, "r": r, "rm": rm, "raised": raised, "base": len(base)})
        md.append(f"| {c['case_id']} | {len(base)} | {v} ({vm}) | {u} ({um}) | {r} ({rm}) | {raised} |")
    md.append(f"| **all** | {tot['base']} | {tot['v']} ({tot['vm']}) | {tot['u']} ({tot['um']}) | {tot['r']} ({tot['rm']}) | {tot['raised']} |")
    md += ["", f"Matched share: verified {tot['vm']}/{tot['v']} = {_pct(tot['vm'] / tot['v'] if tot['v'] else 0)}, "
           f"unverified {tot['um']}/{tot['u']} = {_pct(tot['um'] / tot['u'] if tot['u'] else 0)}, "
           f"rejected / withdrawn {tot['rm']}/{tot['r']} = {_pct(tot['rm'] / tot['r'] if tot['r'] else 0)}. "
           "Critic-raised issues (SCI-C...) carry no evidence and are always routed to a human; they are never scored as claims.", ""]
    return md


def unlabeled_admin_section(cases: list[dict], stamp: str, outputs: Path | None = None) -> list[str]:
    full = next(c for c in CONFIGS if c["key"] == "agents_full")
    cnt = collections.Counter()
    for c in cases:
        for p in saved_findings(full, c["case_id"], stamp, outputs):
            if p["domain"] == "administrative" and p["status"] == "verified":
                cnt[p["category"]] += 1
    md = ["## Administrative findings outside the label scope", "",
          "Verified administrative findings of the full system across the five protocols, by category. Package-completeness "
          "items (consent form, insurance, signature page, sponsor statement, referenced documents) are true for every "
          "public registry protocol and were deliberately not labeled; they dominate the administrative false positives of "
          "the charter table.", "", "| Category | Verified findings |", "|---|---|"]
    md += [f"| {k} | {v} |" for k, v in cnt.most_common()]
    return md + [""]


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):      # Windows consoles default to cp1252
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stamp", default=None)
    ap.add_argument("--cases", default=str(ROOT / "eval" / "labeled_cases"))
    ap.add_argument("--cases-glob", default="nct*.json")
    ap.add_argument("--out", default=str(ROOT / "reports" / "results.md"))
    ap.add_argument("--note", default="", help="one line explaining why the run was re-scored (goes into the header)")
    ap.add_argument("--outputs", default=None, help="folder holding the abl-* run directories (default: settings.output_path)")
    ap.add_argument("--results-dir", default=str(RESULTS), help="where the rescore-<stamp>-<when>.json summary goes")
    a = ap.parse_args(argv)
    stamp = a.stamp or latest_stamp()
    outputs = Path(a.outputs) if a.outputs else None
    summary = json.loads((RESULTS / f"ablation-{stamp}.json").read_text(encoding="utf-8"))
    cases = load_cases(Path(a.cases), a.cases_glob)
    started = datetime.fromisoformat(summary["generated"])
    rows_all = rescore(summary, cases, stamp, outputs=outputs)
    rows_sci = rescore(summary, cases, stamp, domain="scientific", outputs=outputs)

    md = render_markdown(rows_all, cases, no_llm=False, started=started, model=summary["model"])
    head, tail = md.split("## Ablation table", 1)
    head += (f"Re-scored {datetime.now().strftime('%Y-%m-%d %H:%M')} by `eval/rescore.py` from the saved findings of run "
             f"`{stamp}` (no new LLM calls){': ' + a.note if a.note else ''}.\n\n")
    md = head + "## Ablation table" + tail
    md += "\n".join(view_table(rows_sci, "Scientific domain only (reduced-scope view)",
                               "Labels and predictions restricted to the scientific domain. The five labeled protocols are "
                               "public registry documents without submission appendices; the labeler recorded what is wrong "
                               "*in the protocol text*, not which package documents are absent, so this view compares like "
                               "with like.") + ["\n"])
    md += "\n".join(critic_section(cases, stamp, outputs) + ["\n"])
    md += "\n".join(unlabeled_admin_section(cases, stamp, outputs))
    out = Path(a.out)
    out.write_text(md, encoding="utf-8")
    Path(a.results_dir).mkdir(parents=True, exist_ok=True)
    (Path(a.results_dir) / f"rescore-{stamp}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json").write_text(
        json.dumps({"stamp": stamp, "note": a.note, "all": rows_all, "scientific": rows_sci}, indent=1, default=str), encoding="utf-8")
    for r in rows_all:
        print(f"ALL  {r['label']:<55} P={_pct(r['verified_precision'])} ({r['matched_verified']}/{r['n_verified']}) R={_pct(r['coverage'])} ({r['tp']}/{r['labels']}) unverified={r['n_unverified']}")
    for r in rows_sci:
        print(f"SCI  {r['label']:<55} P={_pct(r['verified_precision'])} ({r['matched_verified']}/{r['n_verified']}) R={_pct(r['coverage'])} ({r['tp']}/{r['labels']}) unverified={r['n_unverified']}")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
