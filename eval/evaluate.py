"""Evaluate the Rule-Based Baseline and/or the multi-agent pipeline on labeled cases.

    python eval/evaluate.py --mode baseline
    python eval/evaluate.py --mode agents            (needs ANTHROPIC_API_KEY)
    python eval/evaluate.py --mode agents --no-llm   (graph without LLM = sanity check)
    python eval/evaluate.py --mode single            (single-agent baseline: one LLM call, all tools)
    python eval/evaluate.py --mode single --no-llm   (sanity check: rule findings through the single-agent path)

A predicted finding matches an expected one when (domain, category) are equal.
Findings the critic REJECTED or the reviewer WITHDREW are not counted as predictions. Metrics: precision,
recall, F1 per case and micro-averaged, plus runtime and (for agents) tokens.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from protocol_review.pipeline import run_baseline, run_review, run_single_agent  # noqa: E402


def score(expected: list[dict], predicted: list[dict]) -> dict:
    exp = {(e["domain"], e["category"]) for e in expected}
    pred = {(p["domain"], p["category"]) for p in predicted if p.get("status") not in ("rejected", "withdrawn")}
    tp = len(exp & pred)
    fp = len(pred - exp)
    fn = len(exp - pred)
    precision = tp / (tp + fp) if tp + fp else (1.0 if not exp else 0.0)
    recall = tp / (tp + fn) if tp + fn else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "precision": round(precision, 3), "recall": round(recall, 3), "f1": round(f1, 3),
            "missed": sorted(exp - pred), "extra": sorted(pred - exp)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["baseline", "single", "agents"], default="baseline")
    ap.add_argument("--cases", default=str(ROOT / "eval" / "labeled_cases"))
    ap.add_argument("--no-llm", action="store_true")
    ap.add_argument("--out", default=str(ROOT / "eval" / "results"))
    a = ap.parse_args()

    cases = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(Path(a.cases).glob("*.json"))]
    results, totals = [], {"tp": 0, "fp": 0, "fn": 0}
    for c in cases:
        pdf = ROOT / c["pdf"]
        if not pdf.exists():
            print(f"skip {c['case_id']}: {pdf} missing (run samples/make_sample_protocols.py)")
            continue
        t0 = time.perf_counter()
        if a.mode == "baseline":
            res = run_baseline(pdf, nct_id=c.get("nct_id", ""), run_id=f"eval-baseline-{c['case_id']}")
        elif a.mode == "single":
            res = run_single_agent(pdf, nct_id=c.get("nct_id", ""), no_llm=a.no_llm or None,
                                   run_id=f"eval-single-{c['case_id']}-{time.strftime('%H%M%S')}")
        else:
            res = run_review(pdf, source="eval", submitter="eval", nct_id=c.get("nct_id", ""), no_llm=a.no_llm or None)
        dt = round(time.perf_counter() - t0, 1)
        s = score(c["expected_findings"], res["findings"])
        for k in totals:
            totals[k] += s[k]
        row = {"case": c["case_id"], "mode": a.mode, "decision": res["decision"], "expected_decision": c.get("expected_decision"),
               "runtime_s": dt, "n_findings": len(res["findings"]), **s}
        if a.mode in ("agents", "single"):
            row["cost"] = res.get("cost")
        results.append(row)
        print(f"{c['case_id']:<22} P={s['precision']:.2f} R={s['recall']:.2f} F1={s['f1']:.2f} decision={res['decision']} "
              f"(expected {c.get('expected_decision')}) {dt}s")
        if s["missed"]:
            print("   missed:", s["missed"])
        if s["extra"]:
            print("   extra :", s["extra"])

    tp, fp, fn = totals["tp"], totals["fp"], totals["fn"]
    P = tp / (tp + fp) if tp + fp else 0.0
    R = tp / (tp + fn) if tp + fn else 0.0
    F1 = 2 * P * R / (P + R) if P + R else 0.0
    summary = {"mode": a.mode, "cases": len(results), "micro_precision": round(P, 3), "micro_recall": round(R, 3), "micro_f1": round(F1, 3), "per_case": results}
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    f = out / f"{a.mode}{'-nollm' if a.no_llm else ''}-{time.strftime('%Y%m%d-%H%M%S')}.json"
    f.write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(f"\nmicro P={P:.3f} R={R:.3f} F1={F1:.3f}  -> {f}")


if __name__ == "__main__":
    main()
