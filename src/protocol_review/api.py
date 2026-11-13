"""FastAPI receiver: webhooks (Make.com / n8n / Google Drive / email automations),
run inspection and the HITL memory-approval endpoints.

Run with:  python -m uvicorn protocol_review.api:app --reload --port 8040
"""
from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path

import httpx
from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from pydantic import BaseModel, HttpUrl

from . import logs, memory, stats
from .config import PROJECT_ROOT, settings
from .pipeline import new_run_id, run_baseline, run_review, run_single_agent

log = logging.getLogger(__name__)

# The four review configurations of the ablation (charter v1.5). `agents_full` is the production system; the
# other three exist for the evaluation and are selectable from the dashboard for side-by-side comparisons.
REVIEW_CONFIGS = {
    "agents_full": {"label": stats.CONFIG_LABELS["agents_full"], "kind": "agents", "kwargs": {}},
    "agents_no_critic": {"label": stats.CONFIG_LABELS["agents_no_critic"], "kind": "agents", "kwargs": {"no_critic": True}},
    "single_verified": {"label": stats.CONFIG_LABELS["single_verified"], "kind": "single", "kwargs": {"verify": True}},
    "single_no_verification": {"label": stats.CONFIG_LABELS["single_no_verification"], "kind": "single", "kwargs": {"verify": False}},
    "single_tools": {"label": stats.CONFIG_LABELS["single_tools"], "kind": "single", "kwargs": {"verify": True, "tools": True}},
    "agents_no_critic_tools": {"label": stats.CONFIG_LABELS["agents_no_critic_tools"], "kind": "agents", "kwargs": {"no_critic": True, "tool_use": True}},
    "agents_full_tools": {"label": stats.CONFIG_LABELS["agents_full_tools"], "kind": "agents", "kwargs": {"tool_use": True}},
}


def configuration_of(run: dict) -> str:
    """Human label of the review configuration a run used (from its id for ablation runs, else from its state)."""
    label = stats._config_of(run["id"])
    if label != "other":
        return label
    st = run.get("state") or {}
    mode = st.get("mode", "")
    if mode == "single_agent_no_verification":
        return stats.CONFIG_LABELS["single_no_verification"]
    if mode == "single_agent_tools":
        return stats.CONFIG_LABELS["single_tools"]
    if st.get("tool_use"):
        return stats.CONFIG_LABELS["agents_no_critic_tools" if st.get("no_critic") else "agents_full_tools"]
    if mode.startswith("single_agent") or run.get("source") == "single_agent":
        return stats.CONFIG_LABELS["single_verified"]
    if mode == "rule_based_baseline":
        return "rule-based baseline (no LLM)"
    if st.get("no_critic"):
        return stats.CONFIG_LABELS["agents_no_critic"]
    return stats.CONFIG_LABELS["agents_full"]
app = FastAPI(title="Multi-Agent Clinical Trial Protocol Review", version="0.1.0")
logs.setup_file_logging()
UPLOAD_DIR = PROJECT_ROOT / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def require_secret(x_webhook_secret: str = Header(default="")):
    if settings.webhook_secret and x_webhook_secret != settings.webhook_secret:
        raise HTTPException(status_code=401, detail="invalid X-Webhook-Secret")


def _save_upload(run_id: str, data: bytes, original_name: str) -> Path:
    if not data[:5].startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="file is not a PDF")
    if len(data) > 60 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="PDF larger than 60 MB")
    safe = "".join(c for c in Path(original_name).stem if c.isalnum() or c in "-_")[:60] or "protocol"
    target = UPLOAD_DIR / f"{run_id}_{safe}.pdf"
    target.write_bytes(data)
    return target


def _background_review(run_id: str, pdf_path: Path, source: str, submitter: str, nct_id: str,
                       force_scientific: bool = False, config: str = "agents_full"):
    token = logs.current_run_id.set(run_id)
    try:
        log.info("review queued from %s as %s (config=%s, force_scientific=%s)", source, run_id, config, force_scientific)
        memory.update_run(run_id, status="running")
        cfg = REVIEW_CONFIGS[config]
        if cfg["kind"] == "single":
            run_single_agent(pdf_path, nct_id=nct_id, run_id=run_id, **cfg["kwargs"])
            memory.update_run(run_id, source=source, submitter=submitter)   # run_single_agent labels the source itself
        else:
            run_review(pdf_path, source=source, submitter=submitter, nct_id=nct_id, run_id=run_id,
                       force_scientific=force_scientific, **cfg["kwargs"])
    except Exception:
        log.exception("background review failed for %s", run_id)
    finally:
        logs.current_run_id.reset(token)


# ----------------------------------------------------------------- webhooks
@app.post("/webhook/protocol", dependencies=[Depends(require_secret)])
async def webhook_protocol(background: BackgroundTasks, file: UploadFile = File(...), nct_id: str = Form(""),
                           submitter: str = Form(""), source: str = Form("webhook"),
                           force_scientific: bool = Form(False), config: str = Form("agents_full")):
    """Multipart upload (Make/n8n 'HTTP request' module with the Drive file as binary).

    `force_scientific` is the evaluation gate bypass (charter section 2): the scientific stage runs even when
    the administrative gate fails; the decision is unchanged. `config` selects one of the four review
    configurations of the ablation (default: the full system). Both are used by the dashboard for demonstrations
    and comparisons; production integrations leave them at their defaults."""
    if config not in REVIEW_CONFIGS:
        raise HTTPException(status_code=400, detail=f"config must be one of {', '.join(REVIEW_CONFIGS)}")
    run_id = new_run_id()
    path = _save_upload(run_id, await file.read(), file.filename or "protocol.pdf")
    memory.create_run(run_id, source, submitter, str(path))
    background.add_task(_background_review, run_id, path, source, submitter, nct_id, force_scientific, config)
    return {"run_id": run_id, "status": "queued", "status_url": f"/runs/{run_id}", "config": config}


class UrlPayload(BaseModel):
    file_url: HttpUrl
    nct_id: str = ""
    submitter: str = ""
    source: str = "drive"
    file_name: str = "protocol.pdf"


@app.post("/webhook/protocol-url", dependencies=[Depends(require_secret)])
async def webhook_protocol_url(payload: UrlPayload, background: BackgroundTasks):
    """JSON payload with a download link (Google Drive 'webContentLink' / signed URL)."""
    run_id = new_run_id()
    try:
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as c:
            r = await c.get(str(payload.file_url))
            r.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=400, detail=f"could not download file: {exc}")
    path = _save_upload(run_id, r.content, payload.file_name)
    memory.create_run(run_id, payload.source, payload.submitter, str(path))
    background.add_task(_background_review, run_id, path, payload.source, payload.submitter, payload.nct_id)
    return {"run_id": run_id, "status": "queued", "status_url": f"/runs/{run_id}"}


@app.post("/baseline", dependencies=[Depends(require_secret)])
async def baseline(file: UploadFile = File(...), nct_id: str = Form("")):
    """Synchronous rule-based baseline (no agents) - useful for Checkpoint 1 demos."""
    run_id = new_run_id()
    path = _save_upload(run_id, await file.read(), file.filename or "protocol.pdf")
    return run_baseline(path, nct_id=nct_id, run_id=run_id)


# --------------------------------------------------------------------- runs
@app.get("/runs")
def runs(limit: int = 50):
    return memory.list_runs(limit)


@app.get("/runs/{run_id}")
def run_detail(run_id: str):
    run = memory.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    return run


@app.get("/runs/{run_id}/report")
def run_report(run_id: str, kind: str = "final"):
    run = memory.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    paths = (run.get("state") or {}).get("report_paths") or {}
    key = {"final": "final_report", "admin": "administrative_report", "scientific": "scientific_report"}.get(kind, kind)
    if key not in paths or not Path(paths[key]).exists():
        raise HTTPException(status_code=404, detail=f"report '{kind}' not available (status={run['status']})")
    return FileResponse(paths[key], media_type="text/markdown", filename=Path(paths[key]).name)


@app.get("/runs/{run_id}/messages")
def run_messages(run_id: str):
    """Short-term memory: the agents' conversation on the blackboard."""
    return memory.get_messages(run_id)


@app.get("/runs/{run_id}/cost")
def run_cost(run_id: str):
    return memory.run_cost_summary(run_id)


def _critic_rounds(st: dict) -> list[dict]:
    """The exchange between the critic and the reviewer, rebuilt from the saved state of a run.

    For round i: the critic's verdicts (CriticReport i), the exact revision block the reviewer then received
    (same construction as agents/scientific_critic.py + scientific_reviewer._user_prompt), and what the reviewer
    answered in round i+1 (ScientificReport i+1) as a diff against its round-i findings."""
    rounds = []
    sci = st.get("scientific_reports") or []
    crs = st.get("critic_reports") or []
    for i, cr in enumerate(crs):
        verdicts = cr.get("verdicts") or []
        missed = cr.get("missed_issues") or []
        last_round = i >= settings.max_revise_rounds
        requests = [f"{v.get('finding_id')}: {v.get('notes', '')}" for v in verdicts if v.get("verdict") == "revise"]
        if not last_round:
            requests += [f"MISSED: {m}" for m in missed]
        handoff = ("# REVISION ROUND - critic feedback you must address\n" + "\n".join(f"- {r}" for r in requests)) if requests else ""
        before = {f["id"]: f for f in (sci[i].get("findings") or []) if f.get("source") == "llm"} if i < len(sci) else {}
        after_report = sci[i + 1] if i + 1 < len(sci) else None
        answer = None
        if after_report is not None:
            after = {f["id"]: f for f in (after_report.get("findings") or []) if f.get("source") == "llm" and f.get("status") != "withdrawn"}
            def row(f, kind):
                return {"id": f["id"], "kind": kind, "title": f.get("title", ""), "severity": f.get("severity"),
                        "category": f.get("category"), "pages": [e.get("page") for e in f.get("evidence") or []]}
            changed = [row(after[k], "changed") for k in after if k in before and
                       (after[k].get("title"), after[k].get("description"), after[k].get("severity"), after[k].get("evidence")) !=
                       (before[k].get("title"), before[k].get("description"), before[k].get("severity"), before[k].get("evidence"))]
            kept = [row(after[k], "kept") for k in after if k in before and not any(c["id"] == k for c in changed)]
            new = [row(after[k], "new") for k in after if k not in before]
            withdrawn = [row(before[k], "withdrawn") for k in before if k not in after]
            answer = {"summary": after_report.get("summary", ""), "n_findings": len(after_report.get("findings") or []),
                      "changed": changed, "new": new, "withdrawn": withdrawn, "kept": kept}
        rounds.append({
            "round": cr.get("round", i), "summary": cr.get("summary", ""),
            "counts": {k: sum(1 for v in verdicts if v.get("verdict") == k) for k in ("verified", "revise", "unverified", "rejected")},
            "verdicts": [{"finding_id": v.get("finding_id"), "verdict": v.get("verdict"), "notes": v.get("notes", ""),
                          "revised_severity": v.get("revised_severity")} for v in verdicts],
            "missed_issues": missed, "requests": requests, "handoff_text": handoff, "reviewer_answer": answer,
            "reviewer_findings_after": answer["n_findings"] if answer else None,
        })
    return rounds


@app.get("/runs/{run_id}/summary")
def run_summary(run_id: str):
    """Compact end-of-run view for the dashboard: decision, score, finding counts, summary text, reports, cost."""
    run = memory.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    st = run.get("state") or {}
    findings = st.get("findings") or []
    if not findings and (st.get("paths") or {}).get("findings"):      # single agent: findings kept in a file
        p = Path(st["paths"]["findings"])
        if p.exists():
            findings = json.loads(p.read_text(encoding="utf-8"))

    def count(key):
        out: dict[str, int] = {}
        for f in findings:
            out[f.get(key) or "-"] = out.get(f.get(key) or "-", 0) + 1
        return out
    score = st.get("score")
    return {
        "run_id": run_id, "status": run["status"], "configuration": configuration_of(run),
        "decision": run.get("decision") or st.get("decision") or "",
        "decision_rationale": st.get("decision_rationale", ""), "nct_id": run.get("nct_id") or st.get("nct_id", ""),
        "score": score.get("score") if isinstance(score, dict) else score,
        "pending_human_review": score.get("pending_human_review") if isinstance(score, dict) else None,
        "n_findings": len(findings), "by_status": count("status"), "by_severity": count("severity"), "by_domain": count("domain"),
        "revise_rounds": st.get("revise_rounds", 0), "force_scientific": bool(st.get("force_scientific")),
        "tool_use": bool(st.get("tool_use")) or st.get("mode") == "single_agent_tools",
        "agent_failures": st.get("agent_failures") or [],
        "study_design": (st.get("study_design") or {}).get("kind", ""),
        "critic_rounds": _critic_rounds(st),    # the critic -> reviewer exchange, round by round
        "final_summary": st.get("final_summary", ""), "error": st.get("error"),
        "reports": {k: f"/runs/{run_id}/report?kind={k}" for k, key in
                    (("final", "final_report"), ("admin", "administrative_report"), ("scientific", "scientific_report"))
                    if (st.get("report_paths") or {}).get(key)},
        "cost": memory.run_cost_summary(run_id), "created_at": run.get("created_at"), "finished_at": run.get("finished_at"),
        "protocol_meta": {k: v for k, v in (st.get("protocol_meta") or {}).items() if k in
                          ("title", "nct_id", "version", "date", "principal_investigator", "sponsor", "phase", "page_count")},
    }


@app.get("/runs/{run_id}/compare")
def run_compare(run_id: str):
    """The same protocol under the four review configurations: for the protocol of `run_id` (matched by NCT id,
    else by PDF file name), the latest finished run of every configuration with its cost and finding counts."""
    run = memory.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")

    def key_of(r: dict) -> str:
        return (r.get("nct_id") or "").upper() or Path(r.get("pdf_path") or "").stem.split("_")[-1].lower()
    key = key_of(run)
    rows: dict[str, dict] = {}
    for r in memory.list_runs(1000):
        if r["status"] != "done":
            continue
        full = memory.get_run(r["id"])
        if not full or key_of(full) != key:
            continue
        label = configuration_of(full)
        if label == "rule-based baseline (no LLM)":
            continue
        if label not in rows or (full.get("created_at") or "") > (rows[label]["created_at"] or ""):
            s = run_summary(r["id"])
            rows[label] = {"configuration": label, "run_id": r["id"], "created_at": full.get("created_at"),
                           "decision": s["decision"], "n_findings": s["n_findings"], "verified": s["by_status"].get("verified", 0),
                           "unverified": s["by_status"].get("unverified", 0), "revise_rounds": s["revise_rounds"],
                           "force_scientific": s["force_scientific"], **s["cost"]}
    def row_order(label: str):           # 1, 2, 2', 3, 3', 4, 4', then anything else
        return (label[:1] if label[:1].isdigit() else "9", "'" in label[:2])
    return {"run_id": run_id, "protocol": key, "rows": sorted(rows.values(), key=lambda x: row_order(x["configuration"]))}


# ------------------------------------------------------------- statistics
@app.get("/stats/usage")
def stats_usage(run: str = "", contains: str = "", by: str = "agent"):
    if by not in ("agent", "run", "model", "config"):
        raise HTTPException(status_code=400, detail="by must be agent, run, model or config")
    return stats.usage(run, by, contains)


@app.get("/stats/communications")
def stats_communications(run: str = "", contains: str = ""):
    return stats.communications(run, contains)


@app.get("/stats/results")
def stats_results():
    """Evaluation results (precision / recall per configuration and per labeled protocol) from the latest
    `eval/results/rescore-<stamp>-<when>.json` written by eval/rescore.py. 404 when no evaluation has been run."""
    files = sorted((PROJECT_ROOT / "eval" / "results").glob("rescore-*.json"))
    if not files:
        raise HTTPException(status_code=404, detail="no evaluation results (run eval/ablation.py then eval/rescore.py)")
    data = json.loads(files[-1].read_text(encoding="utf-8"))
    parts = files[-1].stem.split("-")          # rescore-<stamp:2>-<when:2>
    data["file"] = files[-1].name
    data["rescored_at"] = "-".join(parts[3:5]) if len(parts) >= 5 else ""
    return data


@app.get("/stats/trace/{run_id}")
def stats_trace(run_id: str):
    """Chronological trace: pipeline step events, LLM calls (with their interaction id) and blackboard messages."""
    return [{**e, "t": e["t"].isoformat() if e["t"] else None} for e in stats.trace(run_id)]


@app.get("/stats/interaction/{interaction_id}")
def stats_interaction(interaction_id: int):
    """One LLM call in full: prompt excerpt and the structured output (click-through from the dashboard trace)."""
    row = stats.interaction(interaction_id)
    if row is None:
        raise HTTPException(status_code=404, detail="interaction not found")
    return {**row, "t": row["t"].isoformat() if row["t"] else None}


@app.get("/logs")
def server_logs(lines: int = 200, run: str = "", contains: str = ""):
    """Tail of the server log file (every line stamped with its run id)."""
    return {"file": str(logs.log_file()), "lines": logs.tail(min(max(lines, 1), 2000), run, contains)}


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/dashboard")


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    """Live view: the agents' process on the left, tokens and statistics on the right, the summary at the end."""
    return (Path(__file__).parent / "dashboard.html").read_text(encoding="utf-8")


# ---------------------------------------------------- long-term memory HITL
class MemoryDecision(BaseModel):
    decided_by: str
    fact: str | None = None


@app.get("/memory", dependencies=[Depends(require_secret)])
def memories(status: str | None = "proposed", agent: str | None = None):
    return memory.list_memories(status=status or None, agent=agent)


@app.post("/memory/{memory_id}/approve", dependencies=[Depends(require_secret)])
def approve_memory(memory_id: int, body: MemoryDecision):
    res = memory.decide_memory(memory_id, True, body.decided_by, body.fact)
    if not res:
        raise HTTPException(status_code=404, detail="memory not found")
    return res


@app.post("/memory/{memory_id}/reject", dependencies=[Depends(require_secret)])
def reject_memory(memory_id: int, body: MemoryDecision):
    res = memory.decide_memory(memory_id, False, body.decided_by)
    if not res:
        raise HTTPException(status_code=404, detail="memory not found")
    return res


@app.post("/memory/{memory_id}/deactivate", dependencies=[Depends(require_secret)])
def deactivate(memory_id: int, body: MemoryDecision):
    if not memory.deactivate_memory(memory_id, body.decided_by):
        raise HTTPException(status_code=404, detail="memory not found")
    return {"id": memory_id, "status": "inactive"}


@app.get("/health")
def health():
    return {"status": "ok", "model": settings.llm_model, "agent_models": dict(settings.llm_agent_models or {}),
            "no_llm": settings.no_llm, "email_dry_run": settings.email_dry_run}


@app.exception_handler(Exception)
async def unhandled(_, exc: Exception):
    log.exception("unhandled error")
    return JSONResponse(status_code=500, content={"detail": str(exc)})


def cleanup_uploads(keep: int = 200):
    files = sorted(UPLOAD_DIR.glob("*.pdf"), key=lambda p: p.stat().st_mtime, reverse=True)
    for p in files[keep:]:
        p.unlink(missing_ok=True)
    shutil.rmtree(UPLOAD_DIR / "tmp", ignore_errors=True)
