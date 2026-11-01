"""Command line:  python -m protocol_review.cli <command>

  review  <pdf> [--nct NCT...] [--no-llm] [--submitter x]   full multi-agent review
          [--force-scientific] [--no-critic]                evaluation switches (gate bypass / critic ablation)
  baseline <pdf> [--nct NCT...]                             rule-based baseline only
  single   <pdf> [--nct NCT...] [--no-llm] [--no-verification]  single-agent baseline (one LLM call, all tools)
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
    if hasattr(sys.stdout, "reconfigure"):          # Windows consoles default to cp1252; traces contain unicode
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    p = argparse.ArgumentParser(prog="protocol_review")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("review"); r.add_argument("pdf"); r.add_argument("--nct", default=""); r.add_argument("--no-llm", action="store_true")
    r.add_argument("--submitter", default="cli-user")
    r.add_argument("--force-scientific", action="store_true", help="evaluation: run the scientific stage even when the admin gate fails")
    r.add_argument("--no-critic", action="store_true", help="ablation: skip the Scientific Critic (code-only verification)")
    b = sub.add_parser("baseline"); b.add_argument("pdf"); b.add_argument("--nct", default="")
    g = sub.add_parser("single"); g.add_argument("pdf"); g.add_argument("--nct", default=""); g.add_argument("--no-llm", action="store_true")
    g.add_argument("--no-verification", action="store_true", help="ablation: skip the code-level evidence verification")
    s = sub.add_parser("serve"); s.add_argument("--port", type=int, default=8040); s.add_argument("--host", default="127.0.0.1")
    sub.add_parser("poll-mail"); sub.add_parser("graph"); sub.add_parser("purge-memory")
    st = sub.add_parser("stats", help="LLM calls, tokens and runtime from the historical memory")
    st.add_argument("--run", default="", help="run id or prefix, e.g. abl-agents_full- (default: all runs)")
    st.add_argument("--by", default="agent", choices=["agent", "run", "model", "config"],
                    help="config = compare the four ablation review types (abl-<config>-... runs)")
    st.add_argument("--contains", default="", help="only runs whose id contains this, e.g. the stamp of one ablation session")
    st.add_argument("--trace", default="", metavar="RUN_ID", help="print the chronological messages + LLM calls of one run")
    a = p.parse_args(argv)

    if a.cmd == "review":
        from .pipeline import run_review
        res = run_review(a.pdf, source="cli", submitter=a.submitter, nct_id=a.nct, no_llm=a.no_llm or None,
                         force_scientific=a.force_scientific, no_critic=a.no_critic)
        print(json.dumps({"run_id": res["run_id"], "decision": res["decision"], "findings": len(res["findings"]),
                          "reports": res.get("report_paths"), "notifications": res.get("notifications"), "cost": res.get("cost")}, indent=1))
        print("\n" + res.get("final_summary", ""))
    elif a.cmd == "baseline":
        from .pipeline import run_baseline
        res = run_baseline(a.pdf, nct_id=a.nct)
        print(json.dumps({"decision": res["decision"], "findings": [(f["id"], f["category"], f["severity"]) for f in res["findings"]],
                          "paths": res.get("paths")}, indent=1))
    elif a.cmd == "single":
        from .pipeline import run_single_agent
        res = run_single_agent(a.pdf, nct_id=a.nct, no_llm=a.no_llm or None, verify=not a.no_verification)
        print(json.dumps({"run_id": res["run_id"], "decision": res["decision"],
                          "findings": [(f["id"], f["category"], f["severity"], f["status"]) for f in res["findings"]],
                          "errors": res["errors"], "cost": res.get("cost"), "paths": res.get("paths")}, indent=1))
        print("\n" + res.get("final_summary", ""))
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
    elif a.cmd == "stats":
        from .stats import communications, format_communications, format_trace, format_usage, trace, usage
        if a.trace:
            print(format_trace(a.trace, trace(a.trace)))
        else:
            print(format_usage(usage(a.run, a.by, a.contains)))
            print(format_communications(communications(a.run, a.contains)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
