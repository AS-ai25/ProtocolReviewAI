"""Evaluate the Rule-Based Baseline and/or the multi-agent pipeline on labeled cases.

    python eval/evaluate.py --mode baseline
    python eval/evaluate.py --mode agents            (needs ANTHROPIC_API_KEY)
    python eval/evaluate.py --mode agents --no-llm   (graph without LLM = sanity check)
    python eval/evaluate.py --mode single            (single-agent baseline: one LLM call, all tools)
    python eval/evaluate.py --mode single --no-llm   (sanity check: rule findings through the single-agent path)
    python eval/evaluate.py --mode agents --force-scientific   (gate bypass: scientific stage runs even when the
                                                                admin gate fails; decision unchanged)
    python eval/evaluate.py --mode agents --no-critic          (ablation: no Scientific Critic)
    python eval/evaluate.py --mode single --no-verification    (ablation: no code-level evidence check)

For the 4-row ablation table (Checkpoint 2) use eval/ablation.py.

Matching rule (charter v1.4, eval/matching.py): a predicted finding matches an expected one when the domain is
the same and (the categories are equal or aliases - eval/category_aliases.json - OR the guideline reference is the
same and the page is within +-1). Findings the critic REJECTED or the reviewer WITHDREW are not counted as
predictions. Metrics: precision, recall, F1 per case and micro-averaged, precision of VERIFIED findings and the
unverified count, plus runtime and (for agents) tokens.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "eval"))

from matching import score_findings  # noqa: E402

from protocol_review.pipeline import run_baseline, run_review, run_single_agent  # noqa: E402


def score(expected: list[dict], predicted: list[dict]) -> dict:
    """Shared matching rule; keeps the historical keys (tp/fp/fn/precision/recall/f1/missed/extra)."""
    return score_findings(expected, predicted)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["baseline", "single", "agents"], default="baseline")
    ap.add_argument("--cases", default=str(ROOT / "eval" / "labeled_cases"))
    ap.add_argument("--no-llm", action="store_true")
    ap.add_argument("--out", default=str(ROOT / "eval" / "results"))
    ap.add_argument("--force-scientific", action="store_true", help="agents: run the scientific stage even when the admin gate fails")
    ap.add_argument("--no-critic", action="store_true", help="agents: skip the Scientific Critic (ablation)")
    ap.add_argument("--no-verification", action="store_true", help="single: skip the code-level evidence verification (ablation)")
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
            res = run_single_agent(pdf, nct_id=c.get("nct_id", ""), no_llm=a.no_llm or None, verify=not a.no_verification,
                                   run_id=f"eval-single-{c['case_id']}-{time.strftime('%H%M%S')}")
        else:
            res = run_review(pdf, source="eval", submitter="eval", nct_id=c.get("nct_id", ""), no_llm=a.no_llm or None,
                             force_scientific=a.force_scientific, no_critic=a.no_critic)
        dt = round(time.perf_counter() - t0, 1)
        s = score(c["expected_findings"], res["findings"])
        for k in totals:
            totals[k] += s[k]
        row = {"case": c["case_id"], "mode": a.mode, "decision": res["decision"], "expected_decision": c.get("expected_decision"),
               "runtime_s": dt, "n_findings": len(res["findings"]), **s}
        if a.mode in ("agents", "single"):
            row["cost"] = res.get("cost")
        results.append(row)
        print(f"{c['case_id']:<22} P={s['precision']:.2f} R={s['recall']:.2f} F1={s['f1']:.2f} "
              f"P(verified)={s['verified_precision']:.2f} unverified={s['n_unverified']} decision={res['decision']} "
              f"(expected {c.get('expected_decision')}) {dt}s")
        if s["missed"]:
            print("   missed:", s["missed"])
        if s["extra"]:
            print("   extra :", s["extra"])

    tp, fp, fn = totals["tp"], totals["fp"], totals["fn"]
    P = tp / (tp + fp) if tp + fp else 0.0
    R = tp / (tp + fn) if tp + fn else 0.0
    F1 = 2 * P * R / (P + R) if P + R else 0.0
    summary = {"mode": a.mode, "cases": len(results), "force_scientific": a.force_scientific, "no_critic": a.no_critic,
               "no_verification": a.no_verification, "micro_precision": round(P, 3), "micro_recall": round(R, 3), "micro_f1": round(F1, 3), "per_case": results}
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    f = out / f"{a.mode}{'-nollm' if a.no_llm else ''}-{time.strftime('%Y%m%d-%H%M%S')}.json"
    f.write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(f"\nmicro P={P:.3f} R={R:.3f} F1={F1:.3f}  -> {f}")


if __name__ == "__main__":
    main()
