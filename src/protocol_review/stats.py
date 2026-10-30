"""Token usage and runtime statistics from the historical memory (every LLM call is a row in agent_interactions)."""
from __future__ import annotations

from sqlalchemy import func, select

from .db import Interaction, Run, get_session


def usage(run_prefix: str = "", by: str = "agent") -> dict:
    """Aggregate LLM calls, tokens and duration.

    run_prefix  only runs whose id starts with it ("" = everything); an exact run id works too
    by          "agent" (default), "run" or "model"
    Returns {"rows": [...], "total": {...}, "runs": n}.
    """
    col = {"agent": Interaction.agent, "run": Interaction.run_id, "model": Interaction.model}[by]
    with get_session() as db:
        q = select(col.label("key"), func.count().label("calls"), func.sum(Interaction.input_tokens).label("input_tokens"),
                   func.sum(Interaction.output_tokens).label("output_tokens"), func.sum(Interaction.duration_s).label("duration_s"),
                   func.sum(Interaction.fallback_used).label("fallbacks"))
        if run_prefix:
            q = q.where(Interaction.run_id.like(run_prefix + "%"))
        rows = [dict(r._mapping) for r in db.execute(q.group_by(col).order_by(func.sum(Interaction.input_tokens).desc()))]
        runs_q = select(func.count(func.distinct(Interaction.run_id)))
        if run_prefix:
            runs_q = runs_q.where(Interaction.run_id.like(run_prefix + "%"))
        n_runs = db.execute(runs_q).scalar() or 0
        decisions_q = select(Run.decision, func.count()).group_by(Run.decision)
        if run_prefix:
            decisions_q = decisions_q.where(Run.id.like(run_prefix + "%"))
        decisions = {d or "-": n for d, n in db.execute(decisions_q)}
    total = {"calls": sum(r["calls"] for r in rows), "input_tokens": sum(r["input_tokens"] or 0 for r in rows),
             "output_tokens": sum(r["output_tokens"] or 0 for r in rows), "duration_s": sum(r["duration_s"] or 0 for r in rows),
             "fallbacks": sum(r["fallbacks"] or 0 for r in rows)}
    return {"by": by, "run_prefix": run_prefix, "runs": n_runs, "rows": rows, "total": total, "decisions": decisions}


def format_usage(u: dict) -> str:
    w = max([len(str(r["key"])) for r in u["rows"]] + [8])
    lines = [f"LLM usage{' for runs ' + u['run_prefix'] + '*' if u['run_prefix'] else ' (all runs)'}: {u['runs']} run(s), "
             f"{u['total']['calls']} call(s)", "",
             f"{'by ' + u['by']:<{w}}  {'calls':>6}  {'tokens in':>12}  {'tokens out':>11}  {'time':>9}  {'avg/call':>9}  fallbacks",
             "-" * (w + 68)]
    for r in u["rows"]:
        d = r["duration_s"] or 0
        lines.append(f"{str(r['key']):<{w}}  {r['calls']:>6}  {r['input_tokens'] or 0:>12,}  {r['output_tokens'] or 0:>11,}  "
                     f"{d:>8.0f}s  {d / r['calls'] if r['calls'] else 0:>8.1f}s  {r['fallbacks'] or 0}")
    t = u["total"]
    lines.append("-" * (w + 68))
    lines.append(f"{'total':<{w}}  {t['calls']:>6}  {t['input_tokens']:>12,}  {t['output_tokens']:>11,}  {t['duration_s']:>8.0f}s")
    if u["runs"]:
        lines.append(f"{'per run':<{w}}  {t['calls'] / u['runs']:>6.1f}  {t['input_tokens'] / u['runs']:>12,.0f}  "
                     f"{t['output_tokens'] / u['runs']:>11,.0f}  {t['duration_s'] / u['runs']:>8.0f}s")
    if u["decisions"]:
        lines += ["", "decisions: " + ", ".join(f"{k} {v}" for k, v in sorted(u["decisions"].items()))]
    return "\n".join(lines)
