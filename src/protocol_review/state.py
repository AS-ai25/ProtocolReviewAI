"""Shared State / Blackboard models.

Every agent reads from and writes to the same `ReviewState`. Findings carry
their evidence (page + quote), the guideline reference that justifies them and
a status that the critic / coordinator move through PASS / REVISE / UNVERIFIED.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal, TypedDict

from pydantic import BaseModel, Field


class Domain(str, Enum):
    ADMINISTRATIVE = "administrative"
    SCIENTIFIC = "scientific"


class Severity(str, Enum):
    CRITICAL = "critical"   # blocks committee review (admin) / major scientific flaw
    MAJOR = "major"
    MINOR = "minor"
    INFO = "info"


class FindingStatus(str, Enum):
    PROPOSED = "proposed"       # written by a review agent, not yet criticised
    VERIFIED = "verified"       # critic confirmed evidence + guideline reference
    REVISE = "revise"           # critic asks the reviewer for a focused re-check
    UNVERIFIED = "unverified"   # could not be verified -> human review
    REJECTED = "rejected"       # critic found it unsupported / wrong


class Evidence(BaseModel):
    page: int = Field(description="1-based page number in the protocol PDF, 0 if not applicable")
    quote: str = Field(description="Verbatim excerpt (<= 300 chars) from the protocol supporting the finding")


class Finding(BaseModel):
    id: str = Field(description="Stable id like ADM-001 or SCI-003")
    domain: Domain
    category: str = Field(description="Machine-readable check code, e.g. MISSING_SECTION, REGISTRY_MISMATCH")
    severity: Severity
    title: str
    description: str
    evidence: list[Evidence] = Field(default_factory=list)
    guideline_ref: str = Field(
        default="", description="Reference to a knowledge-base rule, e.g. 'SPIRIT-14' or 'ADMIN-CHK-03'"
    )
    recommendation: str = ""
    status: FindingStatus = FindingStatus.PROPOSED
    critic_notes: str = ""
    source: Literal["rule", "llm"] = "llm"


class ChecklistItem(BaseModel):
    code: str = Field(description="Knowledge-base rule code, e.g. ADMIN-CHK-03")
    satisfied: bool
    note: str = ""


class AdminReport(BaseModel):
    """Structured output of the Administrative Review Agent."""
    accepted: bool = Field(description="True when the protocol is administratively complete enough for scientific review")
    summary: str
    findings: list[Finding]
    checklist: list[ChecklistItem] = Field(default_factory=list)


class RegistryComparison(BaseModel):
    field: str
    protocol_value: str
    registry_value: str
    match: bool


class ScientificReport(BaseModel):
    """Structured output of the Scientific Review Agent."""
    summary: str
    findings: list[Finding]
    registry_comparison: list[RegistryComparison] = Field(
        default_factory=list, description="ClinicalTrials.gov cross-check, one row per compared field"
    )
    open_questions: list[str] = Field(default_factory=list)


class CriticVerdict(BaseModel):
    finding_id: str
    verdict: Literal["verified", "revise", "unverified", "rejected"]
    notes: str
    revised_severity: Severity | None = None


class CriticReport(BaseModel):
    """Structured output of the Scientific Critic Agent."""
    summary: str
    verdicts: list[CriticVerdict]
    missed_issues: list[str] = Field(default_factory=list, description="Issues the reviewer should have caught")
    proposed_memory: list[str] = Field(
        default_factory=list,
        description="Reusable lessons worth remembering for future reviews (go through HITL approval)",
    )


class Decision(str, Enum):
    PASS = "PASS"                              # no blocking issues; report goes to the committee
    RETURNED_ADMIN = "RETURNED_ADMIN"          # administrative blockers -> back to submitter
    MAJOR_CONCERNS = "MAJOR_CONCERNS"          # verified critical/major scientific findings -> committee + submitter
    NEEDS_HUMAN_REVIEW = "NEEDS_HUMAN_REVIEW"  # unverified findings remain -> human reviewer first


class FinalSummary(BaseModel):
    """Coordinator's executive summary for the committee coordinator ("the boss")."""
    executive_summary: str = Field(description="5-8 sentences, plain language, for a committee coordinator")
    key_findings: list[str] = Field(description="Most important findings, one line each, with finding ids")
    recommendation: str = Field(description="What the coordinator should do next")


class SingleAgentReport(BaseModel):
    """Structured output of the Single-Agent Baseline: one Claude call that plays
    administrative reviewer, scientific reviewer, critic and coordinator at once."""
    admin_accepted: bool = Field(description="True when no BLOCKING administrative checklist item fails")
    admin_summary: str = Field(description="Administrative completeness in 2-4 sentences")
    scientific_summary: str = Field(description="Scientific / methodological quality in 3-6 sentences")
    findings: list[Finding] = Field(description="All findings, administrative and scientific, each with evidence and guideline_ref")
    checklist: list[ChecklistItem] = Field(default_factory=list)
    registry_comparison: list[RegistryComparison] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    executive_summary: str = Field(description="5-8 sentences for the committee coordinator")
    recommendation: str = Field(description="What the coordinator should do next")


class RegistryRecord(BaseModel):
    nct_id: str
    found: bool = False
    title: str = ""
    phase: str = ""
    status: str = ""
    enrollment: int | None = None
    conditions: list[str] = Field(default_factory=list)
    interventions: list[str] = Field(default_factory=list)
    primary_outcomes: list[str] = Field(default_factory=list)
    sponsor: str = ""
    raw: dict[str, Any] = Field(default_factory=dict)
    error: str = ""


class ReviewState(TypedDict, total=False):
    """LangGraph state = the Blackboard."""
    run_id: str
    source: str                 # webhook | email | cli
    submitter: str
    pdf_path: str
    pdf_text: str               # full text with page markers
    pages: list[dict]           # [{page, text}]
    nct_id: str
    protocol_meta: dict         # title, version, date, sponsor, PI ... extracted deterministically
    rule_findings: list[dict]   # deterministic checks output (shared with baseline)
    admin_report: dict | None
    admin_ok: bool
    registry: dict | None
    scientific_report: dict | None
    critic_report: dict | None
    findings: list[dict]        # consolidated blackboard findings
    revise_rounds: int
    revise_requests: list[str]  # critic questions for the next reviewer pass
    decision: str
    final_summary: str
    report_paths: dict
    notifications: list[str]
    trace: list[dict]           # [{ts, agent, event, detail}]
    errors: list[str]


def trace_event(state: ReviewState, agent: str, event: str, detail: str = "") -> list[dict]:
    items = list(state.get("trace") or [])
    items.append({
        "ts": datetime.utcnow().isoformat(timespec="seconds"),
        "agent": agent,
        "event": event,
        "detail": detail[:500],
    })
    return items
