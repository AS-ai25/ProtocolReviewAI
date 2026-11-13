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
import random
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "eval"))

from ablation import ALL_CONFIGS, CONFIGS, ROW_NUM, load_cases, render_markdown  # noqa: E402
from matching import score_findings  # noqa: E402
from protocol_review.config import settings  # noqa: E402

RESULTS = ROOT / "eval" / "results"
OUTPUTS = settings.output_path   # overridable with --outputs (the tests redirect OUTPUT_DIR to a temp folder)


def latest_stamp() -> str:
    runs = sorted(p for p in RESULTS.glob("ablation-*.json") if "nollm" not in p.name)
    if not runs:
        raise SystemExit("no live ablation run in eval/results/")
    return runs[-1].stem.replace("ablation-", "")


CODE_RE = re.compile(r"ADMIN-CHK-\d{2}|SPIRIT-\d{1,2}[a-dA-D]?|GCP-\d{2}")
CODE_ONLY_ROWS = {"single_verified", "agents_no_critic"}     # rows whose finding status is decided by code alone
SUBITEM_NOTE = "[re-scored: guideline code was valid; sub-item regex bug fixed 2026-11-04] "


def apply_subitem_code_fix(preds: list[dict], codes: set[str]) -> tuple[list[dict], int]:
    """Undo the sub-item code bug on saved code-only findings, without any LLM call.

    Until 2026-11-04 `verify_evidence` read "SPIRIT-27b" as "SPIRIT-27" (unknown) and the code-only rows demoted such
    findings to unverified with the note "Guideline code missing or unknown". A finding whose quotes were located and
    whose codes are all in `codes` (the knowledge base of the run) gets the status the fixed code gives: verified.
    The saved files are not modified; the correction is applied in memory and reported in the results header."""
    out, n = [], 0
    for f in preds:
        f = dict(f)
        v = f.get("evidence_check") or {}
        if (f.get("source") == "llm" and f.get("status") == "unverified" and "uideline code" in (f.get("critic_notes") or "")
                and not (v.get("evidence_checked") and v.get("evidence_found", 0) < v.get("evidence_checked", 0))):
            refs = [c[:-1] + c[-1].lower() if c[-1].isalpha() else c for c in CODE_RE.findall(f.get("guideline_ref") or "")]
            if refs and all(r in codes for r in refs):
                f["status"] = "verified"
                f["critic_notes"] = SUBITEM_NOTE + f["critic_notes"]
                n += 1
        out.append(f)
    return out, n


def saved_findings(cfg: dict, case_id: str, stamp: str, outputs: Path | None = None,
                   fix_codes: set[str] | None = None) -> list[dict]:
    d = (outputs or OUTPUTS) / f"abl-{cfg['key']}-{case_id}-{stamp}"
    f = d / ("single_agent_findings.json" if cfg["kind"] == "single" else "findings.json")
    if not f.exists():
        raise SystemExit(f"missing {f}")
    preds = json.loads(f.read_text(encoding="utf-8"))
    if fix_codes is not None and cfg["key"] in CODE_ONLY_ROWS:
        preds, _ = apply_subitem_code_fix(preds, fix_codes)
    return preds


def rescore(summary: dict, cases: list[dict], stamp: str, *, domain: str | None = None,
            outputs: Path | None = None, fix_codes: set[str] | None = None, stamp_by_key: dict[str, str] | None = None,
            rules_row: bool = True) -> list[dict]:
    """Rebuild the ablation rows from the saved findings; `domain` restricts labels and predictions.
    `stamp_by_key` lets rows of several runs (stamps) share one table; `rules_row` adds row 0 (the 29 deterministic
    checks alone, no LLM) computed from the rule findings saved with any configuration."""
    cost_by = {(r["key"], pc["case"]): pc for r in summary["rows"] for pc in r["per_case"]}
    stamp_by_key = stamp_by_key or {}
    rows = []
    present = {r["key"] for r in summary["rows"]}
    if rules_row and present:
        src_cfg = next(c for c in ALL_CONFIGS if c["key"] in present)
        per_case, totals = [], {"labels": 0, "tp": 0, "n_verified": 0, "matched_verified": 0, "n_unverified": 0,
                                "llm_calls": 0, "input_tokens": 0, "output_tokens": 0, "runtime_s": 0.0}
        for c in cases:
            preds = [f for f in saved_findings(src_cfg, c["case_id"], stamp_by_key.get(src_cfg["key"], stamp), outputs)
                     if f.get("source") == "rule"]
            labels = c["expected_findings"]
            if domain:
                preds = [f for f in preds if f.get("domain") == domain]
                labels = [x for x in labels if x.get("domain") == domain]
            sc = score_findings(labels, preds)
            per_case.append({"case": c["case_id"], "decision": "-", "expected_decision": cost_by[(src_cfg["key"], c["case_id"])]["expected_decision"],
                             "runtime_s": 0.0, "n_findings": len(preds), "llm_calls": 0, "input_tokens": 0, "output_tokens": 0, **sc})
            totals["labels"] += sc["n_labels"]; totals["tp"] += sc["tp"]; totals["n_verified"] += sc["n_verified"]
            totals["matched_verified"] += sc["matched_verified"]; totals["n_unverified"] += sc["n_unverified"]
        rows.append({"key": "rules_only", "label": "Rules only (29 deterministic checks, no LLM)", "kind": "rules", "kwargs": {},
                     "verified_precision": round(totals["matched_verified"] / totals["n_verified"], 3) if totals["n_verified"] else 0.0,
                     "coverage": round(totals["tp"] / totals["labels"], 3) if totals["labels"] else 1.0, **totals, "per_case": per_case})
    for cfg in ALL_CONFIGS:
        if cfg["key"] not in present:
            continue
        row_stamp = stamp_by_key.get(cfg["key"], stamp)
        per_case, totals = [], {"labels": 0, "tp": 0, "n_verified": 0, "matched_verified": 0, "n_unverified": 0,
                                "llm_calls": 0, "input_tokens": 0, "output_tokens": 0, "runtime_s": 0.0}
        for c in cases:
            preds = saved_findings(cfg, c["case_id"], row_stamp, outputs, fix_codes)
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
        md.append(f"| {ROW_NUM.get(r['key'], i)} | {r['label']} | {_pct(r['verified_precision'])} ({r['matched_verified']}/{r['n_verified']}) | "
                  f"{_pct(r['coverage'])} ({r['tp']}/{r['labels']}) | {r['n_unverified']} |")
    md += ["", "| Configuration | Case | Verified | Matched verified | Unverified | Coverage | Missed labels |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        for c in r["per_case"]:
            md.append(f"| {r['label']} | {c['case']} | {c['n_verified']} | {c['matched_verified']} | {c['n_unverified']} | "
                      f"{c['tp']}/{c['n_labels']} | {', '.join(x[1] for x in c['missed']) or '-'} |")
    return md + [""]


FROZEN_BASES = ("single_no_verification", "single_verified", "agents_no_critic")
# Gaps reported by the bootstrap: the frozen full system against the frozen baselines (mentor M2), and every v1.7
# tool-use row against the frozen rows and against the other tool-use rows (2' is the fair baseline for 4').
GAP_PAIRS = ([("agents_full", b) for b in FROZEN_BASES]
             + [("agents_full_tools", b) for b in FROZEN_BASES + ("agents_full", "single_tools", "agents_no_critic_tools")]
             + [("agents_no_critic_tools", b) for b in FROZEN_BASES + ("agents_full", "single_tools")]
             + [("single_tools", b) for b in FROZEN_BASES + ("agents_full",)]
             # model comparison (mentor M8): another model in the full system against Opus (frozen row 4 and the tool-use row 4')
             + [(m, b) for m in ("agents_full_v17", "agents_full_sonnet", "agents_full_haiku", "agents_full_hybrid")
                for b in ("single_verified", "agents_full", "agents_full_tools")]
             + [("agents_full_hybrid", "agents_full_sonnet"), ("agents_full_hybrid", "agents_full_v17")]
             + [("agents_full_sonnet", "agents_full_v17"), ("agents_full_haiku", "agents_full_v17"),
                ("agents_full_sonnet", "agents_full_haiku")])


def bootstrap(rows: list[dict], B: int = 2000, seed: int = 20261108) -> dict:
    """Protocol-level bootstrap (M2, mentor 8 Nov): resample the labeled protocols with replacement, recompute the pooled
    precision and recall of every row and the gap between the main rows and every baseline row. Reports 95% percentile
    intervals and the share of resamples in which the gap is <= 0. With five protocols this is the honest uncertainty."""
    rng = random.Random(seed)
    n = len(rows[0]["per_case"]) if rows else 0
    if n < 2:
        return {}
    samples = [[rng.randrange(n) for _ in range(n)] for _ in range(B)]

    def pooled(row, idx):
        pc = row["per_case"]
        tp = sum(pc[i]["tp"] for i in idx); lab = sum(pc[i]["n_labels"] for i in idx)
        mv = sum(pc[i]["matched_verified"] for i in idx); nv = sum(pc[i]["n_verified"] for i in idx)
        return (mv / nv if nv else 0.0, tp / lab if lab else 0.0)

    def ci(values):
        v = sorted(values)
        return [round(v[int(0.025 * (len(v) - 1))], 3), round(v[int(0.975 * (len(v) - 1))], 3)]

    stats = {r["key"]: [pooled(r, s) for s in samples] for r in rows}
    out = {"B": B, "seed": seed, "n_protocols": n, "rows": {}, "gaps": {}}
    for key, vals in stats.items():
        out["rows"][key] = {"precision_ci95": ci([v[0] for v in vals]), "recall_ci95": ci([v[1] for v in vals])}
    for main, base in GAP_PAIRS:
        if main not in stats or base not in stats:
            continue
        gp = [a[0] - b[0] for a, b in zip(stats[main], stats[base])]
        gr = [a[1] - b[1] for a, b in zip(stats[main], stats[base])]
        out["gaps"][f"{main} vs {base}"] = {
            "precision": {"mean": round(sum(gp) / B, 3), "ci95": ci(gp), "p_le_0": round(sum(1 for g in gp if g <= 0) / B, 3)},
            "recall": {"mean": round(sum(gr) / B, 3), "ci95": ci(gr), "p_le_0": round(sum(1 for g in gr if g <= 0) / B, 3)}}
    return out


def bootstrap_section(bs_all: dict, bs_sci: dict, rows_all: list[dict]) -> list[str]:
    if not bs_all:
        return []
    labels = {r["key"]: f"{ROW_NUM.get(r['key'], '?')} {r['label']}" for r in rows_all}
    md = ["## Uncertainty: protocol-level bootstrap (B=%d, seed %d, %d protocols)" % (bs_all["B"], bs_all["seed"], bs_all["n_protocols"]), "",
          "The five labeled protocols are resampled with replacement; precision and recall are pooled on each resample. "
          "A gap whose 95% interval includes zero (or whose `P(gap <= 0)` is large) is not distinguishable from noise on this "
          "test set. One model run per row: run-to-run variation of the model is not separated from protocol variation here.", "",
          "| Row | Precision 95% CI (all) | Recall 95% CI (all) | Precision 95% CI (scientific) | Recall 95% CI (scientific) |", "|---|---|---|---|---|"]
    for key, lab in labels.items():
        a = bs_all["rows"].get(key); c = (bs_sci or {}).get("rows", {}).get(key)
        if a:
            md.append(f"| {lab} | {_pct(a['precision_ci95'][0])} - {_pct(a['precision_ci95'][1])} | {_pct(a['recall_ci95'][0])} - {_pct(a['recall_ci95'][1])} | "
                      + (f"{_pct(c['precision_ci95'][0])} - {_pct(c['precision_ci95'][1])} | {_pct(c['recall_ci95'][0])} - {_pct(c['recall_ci95'][1])} |" if c else "- | - |"))
    md += ["", "| Gap | View | Precision gap: mean (95% CI), P(gap <= 0) | Recall gap: mean (95% CI), P(gap <= 0) |", "|---|---|---|---|"]
    for view, bs in (("all", bs_all), ("scientific", bs_sci or {})):
        for name, g in (bs.get("gaps") or {}).items():
            main, base = name.split(" vs ")
            md.append(f"| {ROW_NUM.get(main, main)} vs {ROW_NUM.get(base, base)} | {view} | "
                      f"{_pct(g['precision']['mean'])} ({_pct(g['precision']['ci95'][0])} to {_pct(g['precision']['ci95'][1])}), P={g['precision']['p_le_0']:.2f} | "
                      f"{_pct(g['recall']['mean'])} ({_pct(g['recall']['ci95'][0])} to {_pct(g['recall']['ci95'][1])}), P={g['recall']['p_le_0']:.2f} |")
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
    ap.add_argument("--stamp", default=None, help="run stamp; several stamps separated by commas share one table "
                    "(e.g. the frozen 29 Oct run and a v1.7 run of the primed rows)")
    ap.add_argument("--no-rules-row", action="store_true", help="omit row 0 (rules only)")
    ap.add_argument("--bootstrap", type=int, default=2000, help="bootstrap resamples (0 = off)")
    ap.add_argument("--cases", default=str(ROOT / "eval" / "labeled_cases"))
    ap.add_argument("--cases-glob", default="nct*.json")
    ap.add_argument("--out", default=str(ROOT / "reports" / "results.md"))
    ap.add_argument("--note", default="", help="one line explaining why the run was re-scored (goes into the header)")
    ap.add_argument("--outputs", default=None, help="folder holding the abl-* run directories (default: settings.output_path)")
    ap.add_argument("--results-dir", default=str(RESULTS), help="where the rescore-<stamp>-<when>.json summary goes")
    ap.add_argument("--kb-codes", default=None, help="JSON file with the guideline codes of the knowledge base the run used "
                    "(eval/results/kb-v1-codes.json); enables the sub-item code correction of the code-only rows")
    a = ap.parse_args(argv)
    fix_codes = set(json.loads(Path(a.kb_codes).read_text(encoding="utf-8"))["codes"]) if a.kb_codes else None
    stamps = [x.strip() for x in (a.stamp or latest_stamp()).split(",") if x.strip()]
    stamp = stamps[0]
    outputs = Path(a.outputs) if a.outputs else None
    summaries = [json.loads((RESULTS / f"ablation-{st}.json").read_text(encoding="utf-8")) for st in stamps]
    summary = dict(summaries[0])
    stamp_by_key: dict[str, str] = {}
    merged_rows = []
    for st, sm in zip(stamps, summaries):
        for r in sm["rows"]:
            if r["key"] in stamp_by_key:
                continue                                   # the first stamp that has a row keeps it
            stamp_by_key[r["key"]] = st
            merged_rows.append(r)
    summary["rows"] = merged_rows
    cases = load_cases(Path(a.cases), a.cases_glob)
    started = datetime.fromisoformat(summary["generated"])
    rows_all = rescore(summary, cases, stamp, outputs=outputs, fix_codes=fix_codes, stamp_by_key=stamp_by_key, rules_row=not a.no_rules_row)
    rows_sci = rescore(summary, cases, stamp, domain="scientific", outputs=outputs, fix_codes=fix_codes, stamp_by_key=stamp_by_key, rules_row=not a.no_rules_row)
    bs_all = bootstrap(rows_all, B=a.bootstrap) if a.bootstrap else {}
    bs_sci = bootstrap(rows_sci, B=a.bootstrap) if a.bootstrap else {}
    fixed_note = ""
    if fix_codes is not None:
        n_fixed = {cfg["key"]: sum(apply_subitem_code_fix(saved_findings(cfg, c["case_id"], stamp, outputs), fix_codes)[1]
                                   for c in cases) for cfg in CONFIGS if cfg["key"] in CODE_ONLY_ROWS}
        fixed_note = (" Sub-item guideline-code correction applied to the code-only rows from the saved evidence checks "
                      f"(codes of `{Path(a.kb_codes).name}`): " + ", ".join(f"{k}: {v} findings verified instead of unverified"
                                                                            for k, v in n_fixed.items()) + ".")

    md = render_markdown(rows_all, cases, no_llm=False, started=started, model=summary["model"])
    head, tail = md.split("## Ablation table", 1)
    head += (f"Re-scored {datetime.now().strftime('%Y-%m-%d %H:%M')} by `eval/rescore.py` from the saved findings of run(s) "
             f"`{'`, `'.join(stamps)}` (no new LLM calls){': ' + a.note if a.note else ''}.{fixed_note}"
             + (" Row 0 (rules only) is computed from the deterministic findings saved with the runs." if not a.no_rules_row else "") + "\n\n")
    md = head + "## Ablation table" + tail
    md += "\n".join(view_table(rows_sci, "Scientific domain only (reduced-scope view)",
                               "Labels and predictions restricted to the scientific domain. The five labeled protocols are "
                               "public registry documents without submission appendices; the labeler recorded what is wrong "
                               "*in the protocol text*, not which package documents are absent, so this view compares like "
                               "with like.") + ["\n"])
    md += "\n".join(bootstrap_section(bs_all, bs_sci, rows_all) + ["\n"])
    md += "\n".join(critic_section(cases, stamp, outputs) + ["\n"])
    md += "\n".join(unlabeled_admin_section(cases, stamp, outputs))
    out = Path(a.out)
    out.write_text(md, encoding="utf-8")
    Path(a.results_dir).mkdir(parents=True, exist_ok=True)
    (Path(a.results_dir) / f"rescore-{stamp}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json").write_text(
        json.dumps({"stamp": stamp, "stamps": stamps, "note": a.note + fixed_note, "kb_codes": a.kb_codes and Path(a.kb_codes).name,
                    "all": rows_all, "scientific": rows_sci, "bootstrap": {"all": bs_all, "scientific": bs_sci}}, indent=1, default=str), encoding="utf-8")
    for r in rows_all:
        print(f"ALL  {ROW_NUM.get(r['key'], '?'):>2} {r['label']:<55} P={_pct(r['verified_precision'])} ({r['matched_verified']}/{r['n_verified']}) R={_pct(r['coverage'])} ({r['tp']}/{r['labels']}) unverified={r['n_unverified']}")
    for r in rows_sci:
        print(f"SCI  {r['label']:<55} P={_pct(r['verified_precision'])} ({r['matched_verified']}/{r['n_verified']}) R={_pct(r['coverage'])} ({r['tp']}/{r['labels']}) unverified={r['n_unverified']}")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
