"""FastAPI receiver: webhooks (Make.com / n8n / Google Drive / email automations),
run inspection and the HITL memory-approval endpoints.

Run with:  python -m uvicorn protocol_review.api:app --reload --port 8040
"""
from __future__ import annotations

import logging
import shutil
from pathlib import Path

import httpx
from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, HttpUrl

from . import memory
from .config import PROJECT_ROOT, settings
from .pipeline import new_run_id, run_baseline, run_review

log = logging.getLogger(__name__)
app = FastAPI(title="Multi-Agent Clinical Trial Protocol Review", version="0.1.0")
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


def _background_review(run_id: str, pdf_path: Path, source: str, submitter: str, nct_id: str):
    try:
        run_review(pdf_path, source=source, submitter=submitter, nct_id=nct_id, run_id=run_id)
    except Exception:
        log.exception("background review failed for %s", run_id)


# ----------------------------------------------------------------- webhooks
@app.post("/webhook/protocol", dependencies=[Depends(require_secret)])
async def webhook_protocol(background: BackgroundTasks, file: UploadFile = File(...), nct_id: str = Form(""),
                           submitter: str = Form(""), source: str = Form("webhook")):
    """Multipart upload (Make/n8n 'HTTP request' module with the Drive file as binary)."""
    run_id = new_run_id()
    path = _save_upload(run_id, await file.read(), file.filename or "protocol.pdf")
    memory.create_run(run_id, source, submitter, str(path))
    background.add_task(_background_review, run_id, path, source, submitter, nct_id)
    return {"run_id": run_id, "status": "queued", "status_url": f"/runs/{run_id}"}


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
    return {"status": "ok", "model": settings.llm_model, "no_llm": settings.no_llm, "email_dry_run": settings.email_dry_run}


@app.exception_handler(Exception)
async def unhandled(_, exc: Exception):
    log.exception("unhandled error")
    return JSONResponse(status_code=500, content={"detail": str(exc)})


def cleanup_uploads(keep: int = 200):
    files = sorted(UPLOAD_DIR.glob("*.pdf"), key=lambda p: p.stat().st_mtime, reverse=True)
    for p in files[keep:]:
        p.unlink(missing_ok=True)
    shutil.rmtree(UPLOAD_DIR / "tmp", ignore_errors=True)
