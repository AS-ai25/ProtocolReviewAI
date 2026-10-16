"""Entry points: run the multi-agent review or the rule-based baseline on one PDF."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from pathlib import Path

from . import memory
from .baseline import run_baseline
from .graph import build_graph
from .llm import make_llm

log = logging.getLogger(__name__)


def new_run_id() -> str:
    return datetime.utcnow().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6]


def run_review(pdf_path: str | Path, *, source: str = "cli", submitter: str = "", nct_id: str = "",
               llm=None, registry_fetch=None, run_id: str | None = None, no_llm: bool | None = None) -> dict:
    """Full multi-agent review. Returns the final state (without pdf text)."""
    run_id = run_id or new_run_id()
    pdf_path = str(pdf_path)
    memory.create_run(run_id, source, submitter, pdf_path)
    if llm is None:
        llm = make_llm(on_interaction=memory.interaction_hook(run_id), no_llm=no_llm)
    elif getattr(llm, "on_interaction", None) is None:
        llm.on_interaction = memory.interaction_hook(run_id)  # historical memory for injected clients too
    graph = build_graph(llm, registry_fetch=registry_fetch)
    try:
        final = graph.invoke({"run_id": run_id, "source": source, "submitter": submitter, "pdf_path": pdf_path, "nct_id": nct_id})
    except Exception as exc:
        log.exception("run %s failed", run_id)
        memory.update_run(run_id, status="failed", finished_at=datetime.utcnow(), state={"error": str(exc)})
        raise
    slim = {k: v for k, v in final.items() if k not in ("pdf_text", "pages")}
    slim["cost"] = memory.run_cost_summary(run_id)
    memory.update_run(run_id, status="done", decision=final.get("decision", ""), nct_id=final.get("nct_id", ""),
                      finished_at=datetime.utcnow(), state=slim)
    return slim


__all__ = ["run_review", "run_baseline", "new_run_id"]
