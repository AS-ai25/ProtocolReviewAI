"""LangGraph wiring of the multi-agent workflow + agent authority guard.

    START -> intake (coordinator) -> validate (JSON Validation Tool)
          -> [valid?] no  -> finalize
          -> [valid?] yes -> administrative
          -> [admin_ok?] yes -> scientific_reviewer -> scientific_critic
                                  -> [revise requests & rounds left?] yes -> bump_round -> scientific_reviewer
                                                                        no  -> finalize
          -> [admin_ok?] no  -> finalize
    finalize (coordinator) -> report -> notify (email to the boss) -> END

Authority guard (charter v1.3): every node may write only its permitted ReviewState
keys. The protocol data (`protocol_json`, `pages`, `pdf_text`, `protocol_meta`) is
written once by intake and is immutable afterwards. A violation raises
`AuthorityViolation` and fails the run instead of silently corrupting the state.
"""
from __future__ import annotations

from functools import partial, wraps

from langgraph.graph import END, START, StateGraph

from . import notify, reports
from .agents.administrative import administrative_node
from .agents.coordinator import (bump_round_node, finalize_node, intake_node, route_after_admin, route_after_critic,
                                 route_after_validation, validate_node)
from .agents.scientific_critic import scientific_critic_node
from .agents.scientific_reviewer import scientific_reviewer_node
from .state import ReviewState, trace_event

PROTOCOL_KEYS = {"pdf_text", "pages", "protocol_meta", "protocol_json", "pdf_path", "nct_id"}
COMMON = {"trace", "errors"}
ALLOWED_WRITES: dict[str, set[str]] = {
    "intake": PROTOCOL_KEYS | COMMON | {"rule_findings", "findings", "revise_rounds", "revise_requests", "registry",
                                        "notifications", "scientific_reports", "critic_reports"},
    "validate": COMMON | {"validation", "admin_ok", "findings", "admin_report"},
    "administrative": COMMON | {"admin_report", "admin_ok", "findings"},
    "scientific_reviewer": COMMON | {"registry", "scientific_report", "scientific_reports", "findings"},
    "scientific_critic": COMMON | {"critic_report", "critic_reports", "findings", "revise_requests"},
    "bump_round": COMMON | {"revise_rounds"},
    "finalize": COMMON | {"findings", "decision", "decision_rationale", "score", "final_summary"},
    "report": COMMON | {"report_paths"},
    "notify": COMMON | {"notifications"},
}


class AuthorityViolation(RuntimeError):
    pass


def guarded(name: str, fn):
    allowed = ALLOWED_WRITES[name]

    @wraps(fn)
    def _run(state: ReviewState) -> dict:
        out = fn(state)
        illegal = set(out) - allowed
        if illegal:
            raise AuthorityViolation(f"node '{name}' tried to write {sorted(illegal)}; allowed: {sorted(allowed)}")
        return out
    return _run


def report_node(state: ReviewState) -> dict:
    paths = reports.write_reports(state)
    return {"report_paths": paths, "trace": trace_event(state, "coordinator", "reports_written", ", ".join(paths))}


def notify_node(state: ReviewState) -> dict:
    sent = notify.notify_boss(state)
    return {"notifications": sent, "trace": trace_event(state, "coordinator", "notified", "; ".join(sent))}


def build_graph(llm, registry_fetch=None):
    g = StateGraph(ReviewState)
    g.add_node("intake", guarded("intake", intake_node))
    g.add_node("validate", guarded("validate", validate_node))
    g.add_node("administrative", guarded("administrative", partial(administrative_node, llm=llm)))
    g.add_node("scientific_reviewer", guarded("scientific_reviewer", partial(scientific_reviewer_node, llm=llm, registry_fetch=registry_fetch)))
    g.add_node("scientific_critic", guarded("scientific_critic", partial(scientific_critic_node, llm=llm)))
    g.add_node("bump_round", guarded("bump_round", bump_round_node))
    g.add_node("finalize", guarded("finalize", partial(finalize_node, llm=llm)))
    g.add_node("report", guarded("report", report_node))
    g.add_node("notify", guarded("notify", notify_node))

    g.add_edge(START, "intake")
    g.add_edge("intake", "validate")
    g.add_conditional_edges("validate", route_after_validation, {"administrative": "administrative", "finalize": "finalize"})
    g.add_conditional_edges("administrative", route_after_admin, {"scientific_reviewer": "scientific_reviewer", "finalize": "finalize"})
    g.add_edge("scientific_reviewer", "scientific_critic")
    g.add_conditional_edges("scientific_critic", route_after_critic, {"revise": "bump_round", "finalize": "finalize"})
    g.add_edge("bump_round", "scientific_reviewer")
    g.add_edge("finalize", "report")
    g.add_edge("report", "notify")
    g.add_edge("notify", END)
    return g.compile()


def mermaid() -> str:
    return """flowchart TD
    IN[Intake: PDF -> Drive/Mail webhook] --> C0[Coordinator: parse PDF -> protocol JSON by sections + rule checks]
    C0 --> V{JSON Validation Tool}
    V -->|invalid| F[Coordinator: hybrid decision + summary]
    V -->|valid| A[Administrative Review Agent]
    A -->|100% complete| S[Scientific Review Agent<br/>ClinicalTrials.gov + SPIRIT/GCP KB]
    A -->|any finding| F
    S --> K[Scientific Critic Agent]
    K -->|REVISE, round left| S
    K -->|done| F
    F --> R[Reports: Markdown + PDF]
    R --> M[Email to committee coordinator]
    subgraph Blackboard
      B[(Shared State: protocol JSON (immutable), findings, evidence, status, trace)]
    end
    subgraph Memory
      M1[(short: run messages)]
      M2[(long: HITL lessons)]
      M3[(historical: interactions)]
    end
"""
