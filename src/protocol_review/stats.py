"""Token usage and runtime statistics from the historical memory (every LLM call is a row in agent_interactions)."""
from __future__ import annotations

from sqlalchemy import func, select

from .db import Interaction, Run, RunMessage, get_session


CONFIG_LABELS = {"single_no_verification": "1 single LLM call, no verification", "single_verified": "2 single LLM call + code verification",
                 "agents_no_critic": "3 full system without critic", "agents_full": "4 full system (4 agents, critic)",
                 "single_tools": "2' single agent with tool use + code verification",
                 "agents_no_critic_tools": "3' full system without critic, reviewer with tool use",
                 "agents_full_tools": "4' full system, reviewer and critic with tool use",
                 # model comparison (evaluation only): the full system on the current code with another model
                 "agents_full_v17": "4* full system, current code, Opus 5.5",
                 "agents_full_sonnet": "4-S full system, current code, Sonnet 5.5",
                 "agents_full_haiku": "4-H full system, current code, Haiku 5.5"}


def _pattern(prefix: str, contains: str) -> str:
    """SQL LIKE pattern for the run filter; empty when nothing is filtered."""
    if not prefix and not contains:
        return ""
    return f"{prefix}%{contains}%" if contains else f"{prefix}%"


def _config_of(run_id: str) -> str:
    if run_id.startswith("abl-"):
        for cfg in CONFIG_LABELS:
            if run_id.startswith(f"abl-{cfg}-"):
                return CONFIG_LABELS[cfg]
    return "other"


def usage(run_prefix: str = "", by: str = "agent", contains: str = "") -> dict:
    """Aggregate LLM calls, tokens and duration.

    run_prefix  only runs whose id starts with it ("" = everything); an exact run id works too
    contains    only runs whose id contains it (e.g. a stamp, to isolate one ablation session)
    by          "agent" (default), "run", "model" or "config" (ablation configuration: the <cfg> of `abl-<cfg>-<case>-<stamp>`
                run ids - compares the cost of the four review types; other runs land in "other")
    Returns {"rows": [...], "total": {...}, "runs": n}.
    """
    col = {"agent": Interaction.agent, "run": Interaction.run_id, "model": Interaction.model, "config": Interaction.run_id}[by]
    with get_session() as db:
        q = select(col.label("key"), func.count().label("calls"), func.sum(Interaction.input_tokens).label("input_tokens"),
                   func.sum(Interaction.output_tokens).label("output_tokens"), func.sum(Interaction.duration_s).label("duration_s"),
                   func.sum(Interaction.fallback_used).label("fallbacks"))
        pat = _pattern(run_prefix, contains)
        if pat:
            q = q.where(Interaction.run_id.like(pat))
        rows = [dict(r._mapping) for r in db.execute(q.group_by(col).order_by(func.sum(Interaction.input_tokens).desc()))]
        if by == "config":
            merged: dict[str, dict] = {}
            for r in rows:
                key = _config_of(r["key"])
                m = merged.setdefault(key, {"key": key, "calls": 0, "input_tokens": 0, "output_tokens": 0, "duration_s": 0.0, "fallbacks": 0, "runs": 0})
                for k in ("calls", "input_tokens", "output_tokens", "duration_s", "fallbacks"):
                    m[k] += r[k] or 0
                m["runs"] += 1
            rows = sorted(merged.values(), key=lambda m: m["input_tokens"])
        runs_q = select(func.count(func.distinct(Interaction.run_id)))
        if pat:
            runs_q = runs_q.where(Interaction.run_id.like(pat))
        n_runs = db.execute(runs_q).scalar() or 0
        decisions_q = select(Run.decision, func.count()).group_by(Run.decision)
        if pat:
            decisions_q = decisions_q.where(Run.id.like(pat))
        decisions = {d or "-": n for d, n in db.execute(decisions_q)}
    total = {"calls": sum(r["calls"] for r in rows), "input_tokens": sum(r["input_tokens"] or 0 for r in rows),
             "output_tokens": sum(r["output_tokens"] or 0 for r in rows), "duration_s": sum(r["duration_s"] or 0 for r in rows),
             "fallbacks": sum(r["fallbacks"] or 0 for r in rows)}
    return {"by": by, "run_prefix": run_prefix, "runs": n_runs, "rows": rows, "total": total, "decisions": decisions}


def communications(run_prefix: str = "", contains: str = "") -> dict:
    """Agent-to-agent traffic on the Blackboard (short memory) and the bounded revision loop.

    messages      per agent: how many messages it posted (role "agent" = a handoff / result, "system" = coordinator
                  bookkeeping such as intake and validation notes)
    per_run       max / mean messages and LLM calls per run (the "how many interactions" question)
    revisions     revision rounds the critic requested per full run: max, mean, how many runs had one at all
                  (the loop is bounded to one round in code, so max is 1 by construction)
    """
    with get_session() as db:
        mq = select(RunMessage.agent, RunMessage.role, func.count()).where(RunMessage.role != "step") \
            .group_by(RunMessage.agent, RunMessage.role)
        pr = select(RunMessage.run_id, func.count()).where(RunMessage.role != "step").group_by(RunMessage.run_id)
        cq = select(Interaction.run_id, func.count()).group_by(Interaction.run_id)
        rq = select(Run.id, Run.state)
        pat = _pattern(run_prefix, contains)
        if pat:
            mq = mq.where(RunMessage.run_id.like(pat)); pr = pr.where(RunMessage.run_id.like(pat))
            cq = cq.where(Interaction.run_id.like(pat)); rq = rq.where(Run.id.like(pat))
        messages = {}
        for agent, role, n in db.execute(mq):
            messages.setdefault(agent, {})[role] = n
        msgs_per_run = [n for _, n in db.execute(pr)]
        calls_per_run = [n for _, n in db.execute(cq)]
        rounds = []
        for _, state in db.execute(rq):
            if isinstance(state, dict) and "revise_rounds" in state:
                rounds.append(int(state.get("revise_rounds") or 0))

    def stat(xs):
        return {"max": max(xs) if xs else 0, "mean": round(sum(xs) / len(xs), 2) if xs else 0.0, "runs": len(xs)}
    return {"run_prefix": run_prefix, "messages": messages, "messages_per_run": stat(msgs_per_run),
            "calls_per_run": stat(calls_per_run), "revisions": {**stat(rounds), "with_revision": sum(1 for r in rounds if r)}}


def trace(run_id: str) -> list[dict]:
    """Chronological trace of one run: Blackboard messages and LLM calls interleaved (the detailed agent structure)."""
    with get_session() as db:
        msgs = []
        for m in db.execute(select(RunMessage).where(RunMessage.run_id == run_id)).scalars():
            if m.role == "step":                      # pipeline step event: "<event>: <detail>"
                event, _, detail = m.content.partition(": ")
                msgs.append({"t": m.created_at, "kind": "step", "agent": m.agent, "role": m.role, "event": event,
                             "detail": detail, "text": m.content})
            else:
                msgs.append({"t": m.created_at, "kind": "message", "agent": m.agent, "role": m.role, "text": m.content})
        calls = [{"t": i.created_at, "kind": "llm_call", "id": i.id, "agent": i.agent, "model": i.model,
                  "input_tokens": i.input_tokens, "output_tokens": i.output_tokens, "duration_s": i.duration_s,
                  "fallback": bool(i.fallback_used)}
                 for i in db.execute(select(Interaction).where(Interaction.run_id == run_id)).scalars()]
    order = {"step": 0, "llm_call": 1, "message": 2}
    return sorted(msgs + calls, key=lambda e: (e["t"], order[e["kind"]]))


def interaction(interaction_id: int) -> dict | None:
    """One LLM exchange in full (historical memory): what was asked and what came back."""
    with get_session() as db:
        i = db.get(Interaction, interaction_id)
        if i is None:
            return None
        return {"id": i.id, "run_id": i.run_id, "agent": i.agent, "model": i.model, "input_tokens": i.input_tokens,
                "output_tokens": i.output_tokens, "duration_s": i.duration_s, "fallback": bool(i.fallback_used),
                "t": i.created_at, "prompt_excerpt": i.prompt_excerpt, "output": i.output}


def format_trace(run_id: str, events: list[dict]) -> str:
    lines = [f"Trace of run {run_id}: {sum(e['kind'] == 'message' for e in events)} messages, "
             f"{sum(e['kind'] == 'step' for e in events)} step events, {sum(e['kind'] == 'llm_call' for e in events)} LLM calls", ""]
    for e in events:
        t = e["t"].strftime("%H:%M:%S") if e["t"] else "--:--:--"
        if e["kind"] == "llm_call":
            lines.append(f"{t}  [LLM ] {e['agent']:<20} {e['model']}  in {e['input_tokens']:,} / out {e['output_tokens']:,}  "
                         f"{e['duration_s']:.1f}s{'  FALLBACK' if e['fallback'] else ''}")
        elif e["kind"] == "step":
            lines.append(f"{t}  [STEP] {e['agent']:<20} {e['event']}  {e['detail'][:120]}")
        else:
            text = " ".join(e["text"].split())
            lines.append(f"{t}  [{'MSG ' if e['role'] == 'agent' else 'SYS '}] {e['agent']:<20} {text[:150]}")
    return "\n".join(lines)


def format_communications(c: dict) -> str:
    lines = ["", "Agent communications (Blackboard messages)", ""]
    w = max([len(a) for a in c["messages"]] + [8])
    lines.append(f"{'agent':<{w}}  {'handoffs':>9}  {'system notes':>12}")
    for agent, roles in sorted(c["messages"].items(), key=lambda kv: -sum(kv[1].values())):
        lines.append(f"{agent:<{w}}  {roles.get('agent', 0):>9}  {roles.get('system', 0):>12}")
    m, k, r = c["messages_per_run"], c["calls_per_run"], c["revisions"]
    lines += ["", f"per run: messages max {m['max']} / mean {m['mean']}; LLM calls max {k['max']} / mean {k['mean']} ({k['runs']} runs)",
              f"revision rounds (critic -> reviewer, bounded to 1): max {r['max']}, mean {r['mean']}, "
              f"{r['with_revision']} of {r['runs']} full runs had a revision round"]
    return "\n".join(lines)


def format_usage(u: dict) -> str:
    w = max([len(str(r["key"])) for r in u["rows"]] + [8])
    lines = [f"LLM usage{' for runs ' + u['run_prefix'] + '*' if u['run_prefix'] else ' (all runs)'}: {u['runs']} run(s), "
             f"{u['total']['calls']} call(s)", "",
             f"{'by ' + u['by']:<{w}}  {'calls':>6}  {'tokens in':>12}  {'tokens out':>11}  {'time':>9}  {'avg/call':>9}  fallbacks",
             "-" * (w + 68)]
    for r in u["rows"]:
        d = r["duration_s"] or 0
        lines.append(f"{str(r['key']):<{w}}  {r['calls']:>6}  {r['input_tokens'] or 0:>12,}  {r['output_tokens'] or 0:>11,}  "
                     f"{d:>8.0f}s  {d / r['calls'] if r['calls'] else 0:>8.1f}s  {r['fallbacks'] or 0}"
                     + (f"   ({r['runs']} runs: {(r['input_tokens'] or 0) / r['runs']:,.0f} in / {(r['output_tokens'] or 0) / r['runs']:,.0f} out, "
                        f"{d / r['runs']:.0f}s per run)" if u["by"] == "config" and r.get("runs") else ""))
    t = u["total"]
    lines.append("-" * (w + 68))
    lines.append(f"{'total':<{w}}  {t['calls']:>6}  {t['input_tokens']:>12,}  {t['output_tokens']:>11,}  {t['duration_s']:>8.0f}s")
    if u["runs"]:
        lines.append(f"{'per run':<{w}}  {t['calls'] / u['runs']:>6.1f}  {t['input_tokens'] / u['runs']:>12,.0f}  "
                     f"{t['output_tokens'] / u['runs']:>11,.0f}  {t['duration_s'] / u['runs']:>8.0f}s")
    if u["decisions"]:
        lines += ["", "decisions: " + ", ".join(f"{k} {v}" for k, v in sorted(u["decisions"].items()))]
    return "\n".join(lines)
