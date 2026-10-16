"""LangGraph wiring of the multi-agent workflow (five agents).

    START -> intake (coordinator) -> administrative -> administrative_critic
          -> [admin revise requests & rounds left?] yes -> admin_bump_round -> administrative
          -> [admin_ok?] yes -> scientific_reviewer -> scientific_critic
                                  -> [revise requests & rounds left?] yes -> bump_round -> scientific_reviewer
                                                                        no  -> finalize
          -> [admin_ok?] no  -> finalize
    finalize (coordinator) -> report -> notify (email to the boss) -> END
"""
from __future__ import annotations

from functools import partial

from langgraph.graph import END, START, StateGraph

from . import notify, reports
from .agents.administrative import administrative_node
from .agents.administrative_critic import administrative_critic_node
from .agents.coordinator import (admin_bump_round_node, bump_round_node, finalize_node, intake_node, route_after_admin_critic,
                                 route_after_critic)
from .agents.scientific_critic import scientific_critic_node
from .agents.scientific_reviewer import scientific_reviewer_node
from .state import ReviewState, trace_event


def report_node(state: ReviewState) -> dict:
    paths = reports.write_reports(state)
    return {"report_paths": paths, "trace": trace_event(state, "coordinator", "reports_written", ", ".join(paths))}


def notify_node(state: ReviewState) -> dict:
    sent = notify.notify_boss(state)
    return {"notifications": sent, "trace": trace_event(state, "coordinator", "notified", "; ".join(sent))}


def build_graph(llm, registry_fetch=None):
    g = StateGraph(ReviewState)
    g.add_node("intake", intake_node)
    g.add_node("administrative", partial(administrative_node, llm=llm))
    g.add_node("administrative_critic", partial(administrative_critic_node, llm=llm))
    g.add_node("admin_bump_round", admin_bump_round_node)
    g.add_node("scientific_reviewer", partial(scientific_reviewer_node, llm=llm, registry_fetch=registry_fetch))
    g.add_node("scientific_critic", partial(scientific_critic_node, llm=llm))
    g.add_node("bump_round", bump_round_node)
    g.add_node("finalize", partial(finalize_node, llm=llm))
    g.add_node("report", report_node)
    g.add_node("notify", notify_node)

    g.add_edge(START, "intake")
    g.add_edge("intake", "administrative")
    g.add_edge("administrative", "administrative_critic")
    g.add_conditional_edges("administrative_critic", route_after_admin_critic,
                            {"revise": "admin_bump_round", "scientific_reviewer": "scientific_reviewer", "finalize": "finalize"})
    g.add_edge("admin_bump_round", "administrative")
    g.add_edge("scientific_reviewer", "scientific_critic")
    g.add_conditional_edges("scientific_critic", route_after_critic, {"revise": "bump_round", "finalize": "finalize"})
    g.add_edge("bump_round", "scientific_reviewer")
    g.add_edge("finalize", "report")
    g.add_edge("report", "notify")
    g.add_edge("notify", END)
    return g.compile()


def mermaid() -> str:
    return """flowchart TD
    IN[Intake: PDF -> Drive/Mail webhook] --> C0[Coordinator: parse PDF + rule checks]
    C0 --> A[Administrative Review Agent]
    A --> AK[Administrative Critic Agent]
    AK -->|REVISE, round left| A
    AK -->|complete| S[Scientific Review Agent<br/>ClinicalTrials.gov + SPIRIT/GCP KB]
    AK -->|blocking issues| F[Coordinator: decision + summary]
    S --> K[Scientific Critic Agent]
    K -->|REVISE, round left| S
    K -->|done| F
    F --> R[Reports: admin / scientific / final]
    R --> M[Email to committee coordinator]
    subgraph Blackboard
      B[(Shared State: findings, evidence, status, trace)]
    end
    subgraph Memory
      M1[(short: run messages)]
      M2[(long: HITL lessons)]
      M3[(historical: interactions)]
    end
"""
