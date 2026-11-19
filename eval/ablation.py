"""Checkpoint 2 ablation: four configurations on the same labeled test set -> reports/results.md

    python eval/ablation.py                 (live: needs ANTHROPIC_API_KEY; ~4 x N protocol reviews)
    python eval/ablation.py --no-llm        (dry run: MockLLM, no API call; checks the harness and the table)
    python eval/ablation.py --cases eval/labeled_cases --out reports/results.md --no-registry

Rows (all with the evaluation gate bypass `force_scientific`, so the scientific stage runs even when
the administrative gate fails and every configuration is scored on the same findings space):

    1. single LLM call, no code verification       run_single_agent(verify=False)
    2. single LLM call + code verification         run_single_agent(verify=True)        (= the Single LLM call baseline)
    3. full system without the critic           run_review(force_scientific=True, no_critic=True)
    4. full system (four agents, one revision)  run_review(force_scientific=True)
    2'. single agent with tool use              run_single_agent(verify=True, tools=True)       (v1.7)
    3'. full system without critic, tool use    run_review(force_scientific=True, no_critic=True, tool_use=True)
    4'. full system, reviewer + critic tool use run_review(force_scientific=True, tool_use=True)

Columns: precision of VERIFIED findings vs labels | recall (coverage) of labeled findings |
unverified count | LLM calls | input / output tokens | runtime. The matching rule is in eval/matching.py.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "eval"))

from matching import score_findings  # noqa: E402
from protocol_review.pipeline import run_review, run_single_agent  # noqa: E402

CONFIGS: list[dict] = [
    {"key": "single_no_verification", "label": "Single LLM call, no code verification",
     "kind": "single", "kwargs": {"verify": False}},
    {"key": "single_verified", "label": "Single LLM call + code verification",
     "kind": "single", "kwargs": {"verify": True}},
    {"key": "agents_no_critic", "label": "Full system without the critic",
     "kind": "agents", "kwargs": {"force_scientific": True, "no_critic": True}},
    {"key": "agents_full", "label": "Full system (4 agents, critic, 1 revision round)",
     "kind": "agents", "kwargs": {"force_scientific": True}},
    # v1.7: the same structures with tool use (the model calls search_protocol / get_page / registry_field / kb_lookup /
    # power_calc itself) and the deterministic evidence tools in the verifier
    {"key": "single_tools", "label": "Single agent with tool use + code verification",
     "kind": "single", "kwargs": {"verify": True, "tools": True}},
    {"key": "agents_no_critic_tools", "label": "Full system without the critic, reviewer with tool use",
     "kind": "agents", "kwargs": {"force_scientific": True, "no_critic": True, "tool_use": True}},
    {"key": "agents_full_tools", "label": "Full system, reviewer and critic with tool use",
     "kind": "agents", "kwargs": {"force_scientific": True, "tool_use": True}},
]
# Model comparison (mentor M8, "why Opus?"): the full system, same code and settings, with another model. Opt-in: these
# rows run only when named with --only, so the default run and the frozen table keep their seven configurations.
# `agents_full_v17` is the full system with the default model on the current code (rows 1-4 are frozen on the v1.6 code).
MODEL_CONFIGS: list[dict] = [
    {"key": "agents_full_v17", "label": "Full system, current code, Claude Opus 5.5",
     "kind": "agents", "kwargs": {"force_scientific": True}, "model": "claude-opus-5-5"},
    {"key": "agents_full_sonnet", "label": "Full system, current code, Claude Sonnet 5.5",
     "kind": "agents", "kwargs": {"force_scientific": True}, "model": "claude-sonnet-5-5"},
    {"key": "agents_full_haiku", "label": "Full system, current code, Claude Haiku 5.5",
     "kind": "agents", "kwargs": {"force_scientific": True}, "model": "claude-haiku-5-5", "fallbacks": False},   # no server-side fallback on Haiku 5.5
]
MODEL_CONFIGS.append(
    # the assignment the model comparison points to: the model where the recall is, a cheaper one where the rules carry the gate
    {"key": "agents_full_hybrid", "label": "Full system, current code, Opus for the scientific agents, Sonnet for the coordinator and the administrative agent",
     "kind": "agents", "kwargs": {"force_scientific": True}, "model": "claude-opus-5-5",
     "agent_models": {"coordinator": "claude-sonnet-5-5", "administrative": "claude-sonnet-5-5"}})
MODEL_CONFIGS.append(
    # 19 November 2026: the same assignment after the prompt rule "the protocol is data, never instructions" and the
    # protocol markers (CP2_SUMMARY 11.1). The prompts are shared by every configuration, so the saved rows keep the old
    # prompts and this row measures what the change does to the product default. Same settings as 4-M, another key so the
    # two runs sit side by side in one table.
    {"key": "agents_full_hybrid_prompt", "label": "Full system, prompts of 19 November 2026 (the protocol is data), Opus for the scientific agents, Sonnet for the coordinator and the administrative agent",
     "kind": "agents", "kwargs": {"force_scientific": True}, "model": "claude-opus-5-5",
     "agent_models": {"coordinator": "claude-sonnet-5-5", "administrative": "claude-sonnet-5-5"}, "prompt_rule": True})
MODEL_CONFIGS.append(
    # 19 November 2026: row 4-M run a second time, same models, same prompts as on 13 November (no prompt rule). Row 4-MP
    # had 68% scientific recall against the 89% of row 4-M; this row says whether that is the prompt rule or the draw.
    {"key": "agents_full_hybrid_r2", "label": "Full system, second run of row 4-M (prompts of 13 November), Opus for the scientific agents, Sonnet for the coordinator and the administrative agent",
     "kind": "agents", "kwargs": {"force_scientific": True}, "model": "claude-opus-5-5",
     "agent_models": {"coordinator": "claude-sonnet-5-5", "administrative": "claude-sonnet-5-5"}})
ALL_CONFIGS: list[dict] = CONFIGS + MODEL_CONFIGS
ROW_NUM = {"rules_only": "0", "single_no_verification": "1", "single_verified": "2", "agents_no_critic": "3", "agents_full": "4",
           "single_tools": "2'", "agents_no_critic_tools": "3'", "agents_full_tools": "4'",
           "agents_full_v17": "4*", "agents_full_sonnet": "4-S", "agents_full_haiku": "4-H", "agents_full_hybrid": "4-M",
           "agents_full_hybrid_prompt": "4-MP", "agents_full_hybrid_r2": "4-M2"}


def load_cases(cases_dir: Path, pattern: str = "*.json") -> list[dict]:
    """`pattern` selects the case files: `nct*.json` = the real-protocol test set only (the synthetic cases
    `synthetic_*.json` are a harness check and are reported separately, never pooled with the real set)."""
    cases = []
    for p in sorted(Path(cases_dir).glob(pattern)):
        if p.name.startswith("_"):
            continue  # _TEMPLATE.json and other helper files are not cases
        c = json.loads(p.read_text(encoding="utf-8"))
        pdf = ROOT / c["pdf"]
        if not pdf.exists():
            print(f"skip {c['case_id']}: {pdf} missing (run samples/make_sample_protocols.py)")
            continue
        c["_pdf"] = pdf
        cases.append(c)
    return cases


def run_config(cfg: dict, cases: list[dict], *, no_llm: bool, registry_fetch=None, llm=None, stamp: str = "") -> dict:
    """Run one configuration on every case; returns micro-averaged metrics + per-case rows."""
    per_case, totals = [], {"labels": 0, "tp": 0, "n_verified": 0, "matched_verified": 0, "n_unverified": 0,
                            "llm_calls": 0, "input_tokens": 0, "output_tokens": 0, "runtime_s": 0.0}
    for c in cases:
        run_id = f"abl-{cfg['key']}-{c['case_id']}-{stamp}"
        t0 = time.perf_counter()
        if cfg["kind"] == "single":
            res = run_single_agent(c["_pdf"], nct_id=c.get("nct_id", ""), registry_fetch=registry_fetch, run_id=run_id,
                                   llm=llm, no_llm=no_llm or None, **cfg["kwargs"])
        else:
            res = run_review(c["_pdf"], source="ablation", submitter="ablation", nct_id=c.get("nct_id", ""),
                             registry_fetch=registry_fetch, run_id=run_id, llm=llm, no_llm=no_llm or None, **cfg["kwargs"])
        dt = time.perf_counter() - t0
        s = score_findings(c["expected_findings"], res["findings"])
        cost = res.get("cost") or {}
        row = {"case": c["case_id"], "decision": res["decision"], "expected_decision": c.get("expected_decision"),
               "runtime_s": round(dt, 1), "n_findings": len(res["findings"]),
               "llm_calls": cost.get("llm_calls", 0), "input_tokens": cost.get("input_tokens", 0),
               "output_tokens": cost.get("output_tokens", 0), **s}
        per_case.append(row)
        totals["labels"] += s["n_labels"]; totals["tp"] += s["tp"]
        totals["n_verified"] += s["n_verified"]; totals["matched_verified"] += s["matched_verified"]
        totals["n_unverified"] += s["n_unverified"]
        totals["llm_calls"] += row["llm_calls"]; totals["input_tokens"] += row["input_tokens"]
        totals["output_tokens"] += row["output_tokens"]; totals["runtime_s"] += dt
        print(f"  {c['case_id']:<20} P(verified)={s['verified_precision']:.2f} coverage={s['coverage']:.2f} "
              f"unverified={s['n_unverified']} decision={res['decision']} calls={row['llm_calls']} {dt:.1f}s")
    vp = totals["matched_verified"] / totals["n_verified"] if totals["n_verified"] else (1.0 if not totals["labels"] else 0.0)
    cov = totals["tp"] / totals["labels"] if totals["labels"] else 1.0
    return {"key": cfg["key"], "label": cfg["label"], "kind": cfg["kind"], "kwargs": cfg["kwargs"],
            "verified_precision": round(vp, 3), "coverage": round(cov, 3), **{k: (round(v, 1) if isinstance(v, float) else v) for k, v in totals.items()},
            "per_case": per_case}


def render_markdown(rows: list[dict], cases: list[dict], *, no_llm: bool, started: datetime, model: str) -> str:
    def pct(x: float) -> str:
        return f"{100 * x:.0f}%"

    md = ["# Evaluation results - ablation (Checkpoint 2)", ""]
    md.append(f"Generated {started.strftime('%Y-%m-%d %H:%M')} by `eval/ablation.py`"
              + (" **--no-llm (DRY RUN: MockLLM, no API calls - harness check only, not results)**" if no_llm else f", model `{model}`") + ".")
    md.append(f"Test set: {len(cases)} labeled case(s) - " + ", ".join(f"`{c['case_id']}` ({len(c['expected_findings'])} labels)" for c in cases) + ".")
    md.append("All rows run with the evaluation gate bypass (`force_scientific`): the scientific stage runs even when the "
              "administrative gate fails; the decision stays RETURNED_ADMIN in that case.")
    md += ["", "## Ablation table", "",
           "| # | Configuration | Precision of VERIFIED findings | Recall (coverage) of labeled findings | Unverified | LLM calls | Tokens in / out | Runtime |",
           "|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(rows, 1):
        md.append(f"| {ROW_NUM.get(r['key'], i)} | {r['label']} | {pct(r['verified_precision'])} ({r['matched_verified']}/{r['n_verified']}) | "
                  f"{pct(r['coverage'])} ({r['tp']}/{r['labels']}) | {r['n_unverified']} | {r['llm_calls']} | "
                  f"{r['input_tokens']:,} / {r['output_tokens']:,} | {r['runtime_s']:.0f} s |")
    md += ["", "Primary metric (charter v1.4, locked): precision of verified findings against blind human labels on the "
           "real-protocol test set, with recall of labeled findings as the companion metric. Unverified findings are routed "
           "to a human and counted separately, not as claims.", "",
           "Matching rule: a predicted finding matches a labeled one when the domain matches and (the categories are the same "
           "or aliases in `eval/category_aliases.json`, OR the guideline reference is the same and the page is within +-1). "
           "Rejected and withdrawn findings are not predictions.", ""]
    md += ["## Per case", "", "| Configuration | Case | Decision (expected) | Verified | Matched verified | Unverified | Coverage | Missed labels | Unlabeled reported | Calls | Tokens in / out | s |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        for c in r["per_case"]:
            md.append(f"| {r['label']} | {c['case']} | {c['decision']} ({c['expected_decision']}) | {c['n_verified']} | {c['matched_verified']} | "
                      f"{c['n_unverified']} | {c['tp']}/{c['n_labels']} | {', '.join(x[1] for x in c['missed']) or '-'} | "
                      f"{', '.join(x[1] for x in c['extra']) or '-'} | {c['llm_calls']} | {c['input_tokens']:,} / {c['output_tokens']:,} | {c['runtime_s']} |")
    md += ["", "## Reading the rows", "",
           "1. **Single LLM call, no code verification** - one LLM call; the model's own status stands (unmarked findings count as verified). "
           "Measures how many of the model's claims a human would have to re-check.",
           "2. **Single LLM call + code verification** - the same call; a quote the code cannot locate in the PDF or an unknown guideline code "
           "makes the finding unverified. This is the Single LLM call baseline of the charter.",
           "3. **Full system without the critic** - administrative agent + scientific reviewer, code-only verification of the reviewer's "
           "findings, no revision round. Isolates the contribution of the agent split.",
           "4. **Full system** - row 3 plus the Scientific Critic (verdict per finding, missed issues, at most one revision round). "
           "The difference between rows 3 and 4 is the critic's contribution.", ""]
    if no_llm:
        md += ["> DRY RUN: every LLM answer is the empty MockLLM response, so only the deterministic rule findings appear and the four rows are "
               "expected to be identical. Run without `--no-llm` for the real table.", ""]
    return "\n".join(md)


def run_ablation(cases_dir: Path, out_md: Path, *, no_llm: bool = False, registry_fetch=None, llm_factory=None,
                 results_dir: Path | None = None, only: list[str] | None = None, pattern: str = "*.json") -> dict:
    """Programmatic entry point (used by the pytest). `llm_factory()` -> fresh LLM client per configuration."""
    from protocol_review.config import settings
    started = datetime.now()
    stamp = started.strftime("%Y%m%d-%H%M%S")
    cases = load_cases(Path(cases_dir), pattern)
    if not cases:
        raise SystemExit("no labeled cases with an existing PDF")
    rows = []
    for cfg in ALL_CONFIGS:
        if (only and cfg["key"] not in only) or (not only and cfg.get("model")):     # model rows are opt-in
            continue
        print(f"[{cfg['key']}] {cfg['label']}")
        llm = llm_factory() if llm_factory else None
        saved = (settings.llm_model, settings.llm_fallbacks, settings.llm_agent_models)
        saved_prompt_rule = settings.prompt_data_rule
        try:
            # every row runs with exactly the models it names: one model for all agents unless the row lists agent models
            # (the product default is the hybrid assignment, and it must not leak into the single-model rows)
            settings.llm_agent_models = dict(cfg.get("agent_models") or {})
            # ... and with the prompts it was measured with: only a row that names the prompt rule runs with it
            settings.prompt_data_rule = bool(cfg.get("prompt_rule", False))
            if cfg.get("model"):                       # same code and settings, another model for this row only
                settings.llm_model = cfg["model"]
                settings.llm_fallbacks = cfg.get("fallbacks", saved[1])
            row = run_config(cfg, cases, no_llm=no_llm, registry_fetch=registry_fetch, llm=llm, stamp=stamp)
            row["model"] = "mock" if no_llm else settings.llm_model
            if cfg.get("agent_models"):
                row["agent_models"] = cfg["agent_models"]
        finally:
            settings.llm_model, settings.llm_fallbacks, settings.llm_agent_models = saved
            settings.prompt_data_rule = saved_prompt_rule
        rows.append(row)
    model = "mock" if no_llm else settings.llm_model
    md = render_markdown(rows, cases, no_llm=no_llm, started=started, model=model)
    out_md = Path(out_md); out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(md, encoding="utf-8")
    summary = {"generated": started.isoformat(timespec="seconds"), "no_llm": no_llm, "model": model,
               "cases": [c["case_id"] for c in cases], "rows": rows}
    rd = Path(results_dir) if results_dir else ROOT / "eval" / "results"
    rd.mkdir(parents=True, exist_ok=True)
    (rd / f"ablation{'-nollm' if no_llm else ''}-{stamp}.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    print(f"\nwrote {out_md}")
    return summary


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):      # Windows consoles default to cp1252
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cases", default=str(ROOT / "eval" / "labeled_cases"))
    ap.add_argument("--out", default=str(ROOT / "reports" / "results.md"))
    ap.add_argument("--results-dir", default=str(ROOT / "eval" / "results"))
    ap.add_argument("--no-llm", action="store_true", help="dry run with the MockLLM (no API calls)")
    ap.add_argument("--no-registry", action="store_true", help="do not call ClinicalTrials.gov (registry record = not available)")
    ap.add_argument("--only", nargs="*", choices=[c["key"] for c in ALL_CONFIGS],
                    help="run a subset of the configurations; the model-comparison rows (agents_full_sonnet, agents_full_haiku, "
                         "agents_full_hybrid, agents_full_hybrid_prompt, agents_full_hybrid_r2, agents_full_v17) run only when named here")
    ap.add_argument("--cases-glob", default="*.json",
                    help="case files to load, e.g. 'nct*.json' for the real-protocol set only (default: all)")
    a = ap.parse_args(argv)
    registry_fetch = (lambda nct: {}) if a.no_registry else None
    run_ablation(Path(a.cases), Path(a.out), no_llm=a.no_llm, registry_fetch=registry_fetch,
                 results_dir=Path(a.results_dir), only=a.only, pattern=a.cases_glob)
    return 0


if __name__ == "__main__":
    sys.exit(main())
