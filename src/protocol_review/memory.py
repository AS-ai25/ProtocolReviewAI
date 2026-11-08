"""Three-layer agent memory (platform standard).

short      -> `run_messages`: the agents' conversation on the blackboard for one
              run; persisted so a run can be inspected/resumed; purged after
              SHORT_TTL_DAYS.
long       -> `agent_memories`: reusable lessons an agent PROPOSES; a human
              (committee coordinator / admin) approves, edits or rejects via the
              API. Only `approved` facts are injected into prompts. Global scope
              never auto-approves.
historical -> `agent_interactions`: every LLM exchange with tokens/duration for
              audit, cost tracking and evaluation.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select

from .db import AgentMemory, Interaction, Run, RunMessage, get_session
from .llm import LLMResult

SHORT_TTL_DAYS = 7
MAX_MEMORIES_IN_PROMPT = 20


# ------------------------------------------------------------------ runs
def create_run(run_id: str, source: str, submitter: str, pdf_path: str) -> None:
    """Create the run row, or refresh it if the API already queued it."""
    with get_session() as db:
        run = db.get(Run, run_id)
        if run is None:
            db.add(Run(id=run_id, source=source, submitter=submitter, pdf_path=pdf_path, status="queued"))
        else:
            run.source, run.submitter, run.pdf_path = source, submitter, pdf_path
        db.commit()


def update_run(run_id: str, **fields) -> None:
    with get_session() as db:
        run = db.get(Run, run_id)
        if run is None:
            run = Run(id=run_id)
            db.add(run)
        for k, v in fields.items():
            setattr(run, k, v)
        db.commit()


def get_run(run_id: str) -> dict | None:
    with get_session() as db:
        run = db.get(Run, run_id)
        if run is None:
            return None
        return {
            "id": run.id, "source": run.source, "submitter": run.submitter, "pdf_path": run.pdf_path,
            "nct_id": run.nct_id, "status": run.status, "decision": run.decision,
            "created_at": run.created_at.isoformat() if run.created_at else None,
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "state": run.state or {},
        }


def list_runs(limit: int = 50) -> list[dict]:
    with get_session() as db:
        rows = db.execute(select(Run).order_by(Run.created_at.desc()).limit(limit)).scalars().all()
        return [{"id": r.id, "source": r.source, "submitter": r.submitter, "nct_id": r.nct_id, "status": r.status,
                 "decision": r.decision, "created_at": r.created_at.isoformat() if r.created_at else None} for r in rows]


# ----------------------------------------------------------- short memory
def post_message(run_id: str, agent: str, content: str, role: str = "agent") -> None:
    with get_session() as db:
        db.add(RunMessage(run_id=run_id, agent=agent, role=role, content=content[:20000]))
        db.commit()


def get_messages(run_id: str, include_steps: bool = False) -> list[dict]:
    """The agents' conversation (roles agent/system); `step` rows are the pipeline's trace events."""
    with get_session() as db:
        q = select(RunMessage).where(RunMessage.run_id == run_id).order_by(RunMessage.id)
        if not include_steps:
            q = q.where(RunMessage.role != "step")
        rows = db.execute(q).scalars().all()
        return [{"agent": r.agent, "role": r.role, "content": r.content, "ts": r.created_at.isoformat()} for r in rows]


def purge_short_memory(days: int = SHORT_TTL_DAYS) -> int:
    cutoff = datetime.utcnow() - timedelta(days=days)
    with get_session() as db:
        rows = db.execute(select(RunMessage).where(RunMessage.created_at < cutoff)).scalars().all()
        for r in rows:
            db.delete(r)
        db.commit()
        return len(rows)


# ------------------------------------------------------------ long memory
def recall_memories(agent: str, scope_refs: dict[str, str] | None = None) -> list[dict]:
    """Approved facts for this agent: global + matching sponsor/submitter scopes."""
    scope_refs = {k: v for k, v in (scope_refs or {}).items() if v}
    with get_session() as db:
        rows = db.execute(
            select(AgentMemory).where(AgentMemory.agent == agent, AgentMemory.status == "approved")
            .order_by(AgentMemory.decided_at.desc())
        ).scalars().all()
    out = []
    for r in rows:
        if r.scope == "global" or (r.scope in scope_refs and r.scope_ref.lower() in scope_refs[r.scope].lower()):
            out.append({"id": r.id, "scope": r.scope, "scope_ref": r.scope_ref, "fact": r.fact})
    return out[:MAX_MEMORIES_IN_PROMPT]


def memories_block(agent: str, scope_refs: dict[str, str] | None = None) -> str:
    mems = recall_memories(agent, scope_refs)
    if not mems:
        return ""
    lines = ["## Approved lessons from previous reviews (human-approved long-term memory)"]
    for m in mems:
        tag = m["scope"] if m["scope"] == "global" else f"{m['scope']}: {m['scope_ref']}"
        lines.append(f"- [{tag}] {m['fact']}")
    return "\n".join(lines)


def propose_memory(agent: str, fact: str, scope: str = "global", scope_ref: str = "", run_id: str = "",
                   proposed_by: str = "") -> int:
    """Store a PROPOSED fact. Never auto-approves: a human must approve via the API."""
    fact = (fact or "").strip()
    if not fact:
        return 0
    with get_session() as db:
        dup = db.execute(select(AgentMemory).where(AgentMemory.agent == agent, AgentMemory.fact == fact,
                                                  AgentMemory.status.in_(["proposed", "approved"]))).scalar_one_or_none()
        if dup:
            return dup.id
        row = AgentMemory(agent=agent, fact=fact[:2000], scope=scope, scope_ref=scope_ref[:200], run_id=run_id,
                          proposed_by=proposed_by or agent)
        db.add(row)
        db.commit()
        return row.id


def list_memories(status: str | None = None, agent: str | None = None) -> list[dict]:
    with get_session() as db:
        q = select(AgentMemory).order_by(AgentMemory.created_at.desc())
        if status:
            q = q.where(AgentMemory.status == status)
        if agent:
            q = q.where(AgentMemory.agent == agent)
        rows = db.execute(q).scalars().all()
        return [{"id": r.id, "agent": r.agent, "scope": r.scope, "scope_ref": r.scope_ref, "fact": r.fact,
                 "status": r.status, "proposed_by": r.proposed_by, "run_id": r.run_id,
                 "created_at": r.created_at.isoformat(), "decided_by": r.decided_by} for r in rows]


def decide_memory(memory_id: int, approve: bool, decided_by: str, edited_fact: str | None = None) -> dict | None:
    with get_session() as db:
        row = db.get(AgentMemory, memory_id)
        if row is None:
            return None
        row.status = "approved" if approve else "rejected"
        row.decided_by = decided_by
        row.decided_at = datetime.utcnow()
        if edited_fact:
            row.fact = edited_fact[:2000]
        db.commit()
        return {"id": row.id, "status": row.status, "fact": row.fact}


def deactivate_memory(memory_id: int, decided_by: str) -> bool:
    with get_session() as db:
        row = db.get(AgentMemory, memory_id)
        if row is None:
            return False
        row.status = "inactive"
        row.decided_by = decided_by
        row.decided_at = datetime.utcnow()
        db.commit()
        return True


# ------------------------------------------------------ historical memory
def record_interaction(run_id: str, result: LLMResult, system: str, user: str, output: dict) -> None:
    with get_session() as db:
        db.add(Interaction(
            run_id=run_id, agent=result.agent, model=result.model, input_tokens=result.input_tokens,
            output_tokens=result.output_tokens, duration_s=result.duration_s, fallback_used=result.fallback_used,
            prompt_excerpt=_prompt_excerpt(system, user),
            output=({**output, "_tool_calls": result.tool_calls} if result.tool_calls else output),
        ))
        db.commit()


def _prompt_excerpt(system: str, user: str) -> str:
    """Beginning of the system and user prompts plus, when present, the critic's revision requests
    (they sit after the knowledge base in the reviewer's prompt and would otherwise be cut off)."""
    out = system[:1500] + "\n---\n" + user[:3000]
    i = user.find("# REVISION ROUND")
    if i != -1:
        j = user.find("# Protocol text", i)
        out += "\n[...]\n" + user[i:j if j != -1 else i + 6000][:6000]
    return out


def list_interactions(run_id: str) -> list[dict]:
    """Every LLM exchange of a run, oldest first, with the tool calls the agent made (v1.7)."""
    with get_session() as db:
        rows = db.execute(select(Interaction).where(Interaction.run_id == run_id).order_by(Interaction.id)).scalars().all()
    return [{"id": r.id, "agent": r.agent, "model": r.model, "input_tokens": r.input_tokens, "output_tokens": r.output_tokens,
             "duration_s": r.duration_s, "tool_calls": (r.output or {}).get("_tool_calls") or []} for r in rows]


def run_cost_summary(run_id: str) -> dict:
    with get_session() as db:
        rows = db.execute(select(Interaction).where(Interaction.run_id == run_id)).scalars().all()
    return {
        "llm_calls": len(rows),
        "input_tokens": sum(r.input_tokens for r in rows),
        "output_tokens": sum(r.output_tokens for r in rows),
        "duration_s": round(sum(r.duration_s for r in rows), 2),
        "by_agent": {a: sum(1 for r in rows if r.agent == a) for a in sorted({r.agent for r in rows})},
    }


def interaction_hook(run_id: str):
    """Build the `on_interaction` callback for LLM clients of one run."""
    def _hook(result: LLMResult, system: str, user: str, output: dict) -> None:
        record_interaction(run_id, result, system, user, output)
    return _hook
