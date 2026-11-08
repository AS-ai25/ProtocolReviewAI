"""Entry points: run the multi-agent review, the rule-based baseline or the single LLM call baseline on one PDF."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from pathlib import Path

from . import memory
from .logs import current_run_id
from .baseline import run_baseline
from .graph import build_graph
from .llm import make_llm
from .single_agent import run_single_agent

log = logging.getLogger(__name__)


def new_run_id() -> str:
    return datetime.utcnow().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6]


def run_review(pdf_path: str | Path, *, source: str = "cli", submitter: str = "", nct_id: str = "",
               llm=None, registry_fetch=None, run_id: str | None = None, no_llm: bool | None = None,
               force_scientific: bool = False, no_critic: bool = False) -> dict:
    """Full multi-agent review. Returns the final state (without pdf text).

    Evaluation switches (not for production runs):
      force_scientific  run the scientific stage even when the administrative gate fails; the decision is
                        still RETURNED_ADMIN, but the scientific findings are produced and reported.
      no_critic         ablation: skip the Scientific Critic (and the revision round); the reviewer's
                        findings are verified by code only, like the single agent's.
    """
    run_id = run_id or new_run_id()
    token = current_run_id.set(run_id)
    try:
        return _run_review(pdf_path, run_id, source, submitter, nct_id, llm, registry_fetch, no_llm, force_scientific, no_critic)
    finally:
        current_run_id.reset(token)


def _run_review(pdf_path, run_id, source, submitter, nct_id, llm, registry_fetch, no_llm, force_scientific, no_critic) -> dict:
    pdf_path = str(pdf_path)
    log.info("run %s started: %s (source=%s, force_scientific=%s, no_critic=%s)", run_id, Path(pdf_path).name, source,
             force_scientific, no_critic)
    memory.create_run(run_id, source, submitter, pdf_path)
    if llm is None:
        llm = make_llm(on_interaction=memory.interaction_hook(run_id), no_llm=no_llm)
    elif getattr(llm, "on_interaction", None) is None:
        llm.on_interaction = memory.interaction_hook(run_id)  # historical memory for injected clients too
    graph = build_graph(llm, registry_fetch=registry_fetch)
    try:
        initial = {"run_id": run_id, "source": source, "submitter": submitter, "pdf_path": pdf_path, "nct_id": nct_id}
        if force_scientific:
            initial["force_scientific"] = True
        if no_critic:
            initial["no_critic"] = True
        final = graph.invoke(initial)
    except Exception as exc:
        log.exception("run %s failed", run_id)
        memory.update_run(run_id, status="failed", finished_at=datetime.utcnow(), state={"error": str(exc)})
        raise
    slim = {k: v for k, v in final.items() if k not in ("pdf_text", "pages")}
    slim["cost"] = memory.run_cost_summary(run_id)
    memory.update_run(run_id, status="done", decision=final.get("decision", ""), nct_id=final.get("nct_id", ""),
                      finished_at=datetime.utcnow(), state=slim)
    log.info("run %s done: decision=%s findings=%d llm_calls=%d", run_id, final.get("decision", ""),
             len(final.get("findings") or []), slim["cost"]["llm_calls"])
    return slim


__all__ = ["run_review", "run_baseline", "run_single_agent", "new_run_id"]
