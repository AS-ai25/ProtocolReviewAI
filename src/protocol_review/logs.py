"""Server log: every log line goes to a file, stamped with the run it belongs to, so the dashboard can show it.

The run id comes from a context variable set by the pipeline (run_review / run_single_agent) and by the API's
background task; lines outside a run carry "-".
"""
from __future__ import annotations

import contextvars
import logging
from pathlib import Path

from .config import settings

current_run_id: contextvars.ContextVar[str] = contextvars.ContextVar("run_id", default="-")
FORMAT = "%(asctime)s %(levelname)s [%(run_id)s] %(name)s: %(message)s"
_handler: logging.Handler | None = None


class RunIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.run_id = current_run_id.get()
        return True


def log_file() -> Path:
    return Path(settings.log_file)


def setup_file_logging() -> Path:
    """Attach the file handler to the root logger once (idempotent); INFO and above."""
    global _handler
    path = log_file()
    if _handler is None:
        path.parent.mkdir(parents=True, exist_ok=True)
        _handler = logging.FileHandler(path, encoding="utf-8")
        _handler.addFilter(RunIdFilter())
        _handler.setFormatter(logging.Formatter(FORMAT))
        root = logging.getLogger()
        root.addHandler(_handler)
        if root.level == logging.NOTSET or root.level > logging.INFO:
            root.setLevel(logging.INFO)
    return path


def tail(lines: int = 200, run: str = "", contains: str = "") -> list[str]:
    """Last `lines` lines of the log, optionally only those of one run and/or containing a substring."""
    path = log_file()
    if not path.exists():
        return []
    out = []
    with path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if run and f"[{run}]" not in line:
                continue
            if contains and contains.lower() not in line.lower():
                continue
            out.append(line)
    return out[-max(1, lines):]
