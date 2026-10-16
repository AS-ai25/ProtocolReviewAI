"""Command line:  python -m protocol_review.cli <command>

  review  <pdf> [--nct NCT...] [--no-llm] [--submitter x]   full multi-agent review
  baseline <pdf> [--nct NCT...]                             rule-based baseline only
  serve [--port 8040]                                       FastAPI webhook server
  poll-mail                                                 IMAP inbox poller (protocols by email)
  graph                                                     print the Mermaid diagram
  purge-memory                                              delete expired short-term memory
"""
from __future__ import annotations

import argparse
import json
import logging
import sys


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    p = argparse.ArgumentParser(prog="protocol_review")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("review"); r.add_argument("pdf"); r.add_argument("--nct", default=""); r.add_argument("--no-llm", action="store_true")
    r.add_argument("--submitter", default="cli-user")
    b = sub.add_parser("baseline"); b.add_argument("pdf"); b.add_argument("--nct", default="")
    s = sub.add_parser("serve"); s.add_argument("--port", type=int, default=8040); s.add_argument("--host", default="127.0.0.1")
    sub.add_parser("poll-mail"); sub.add_parser("graph"); sub.add_parser("purge-memory")
    a = p.parse_args(argv)

    if a.cmd == "review":
        from .pipeline import run_review
        res = run_review(a.pdf, source="cli", submitter=a.submitter, nct_id=a.nct, no_llm=a.no_llm or None)
        print(json.dumps({"run_id": res["run_id"], "decision": res["decision"], "findings": len(res["findings"]),
                          "reports": res.get("report_paths"), "notifications": res.get("notifications"), "cost": res.get("cost")}, indent=1))
        print("\n" + res.get("final_summary", ""))
    elif a.cmd == "baseline":
        from .pipeline import run_baseline
        res = run_baseline(a.pdf, nct_id=a.nct)
        print(json.dumps({"decision": res["decision"], "findings": [(f["id"], f["category"], f["severity"]) for f in res["findings"]],
                          "paths": res.get("paths")}, indent=1))
    elif a.cmd == "serve":
        import uvicorn
        uvicorn.run("protocol_review.api:app", host=a.host, port=a.port, reload=False)
    elif a.cmd == "poll-mail":
        from .ingest.imap_poller import poll_forever
        poll_forever()
    elif a.cmd == "graph":
        from .graph import mermaid
        print(mermaid())
    elif a.cmd == "purge-memory":
        from .memory import purge_short_memory
        print(f"purged {purge_short_memory()} messages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
