# Project Charter

## Multi-Agent Clinical Trial Protocol Review System

**BIU DS23 Final Project**  
**Team:** Amir Shmaryahu and Ron Levi  
**Date:** 19 October 2026 | **Version:** 1.3 (Ron's revisions of 18 October implemented in code; supersedes v1.2 of 18 October 2026)  
**Repository:** github.com/AS-ai25/ProtocolReviewAI (private)

---

## 1. Problem and Users

Helsinki (IRB / ethics) committee coordinators and professional committee members review complex clinical trial protocols before committee deliberation. The review has two distinct parts: an administrative check (is the submission complete, correctly formatted, with every required document and section) and a scientific check (is the methodology sound, internally consistent, and aligned with the trial registry and with SPIRIT / ICH-GCP expectations). The process is time-consuming and vulnerable to missed findings and human error.

The system supports, but does not replace, professional committee review. Its users are the committee coordinator ("the boss"), who receives every result by email, and committee members, who receive reports in which every finding is traceable to a page, a quote and a guideline item.

## 2. Success Criteria and Evaluation

The system is evaluated on a labeled test set that includes ordinary cases, conflicting information, and cases without a valid resolution.

**Targets (planned, not yet measured on real protocols):**

- F1 score of at least 0.80 for finding detection.
- Improvement of at least 5 percentage points over the Single-Agent Baseline.
- Valid protocol or professional-guideline references for at least 95% of findings labeled as verified.

**Baselines.** Two baselines are implemented in the same repository and emit the same finding format and decision vocabulary as the multi-agent system:

- *Rule-Based Baseline:* the 29 deterministic checks alone (no LLM).
- *Single-Agent Baseline:* one LLM call that receives everything the multi-agent system has (protocol text, both knowledge bases, rule findings, registry record), without a critic and without a revision round.

**Metrics.** Precision, recall and F1 on findings; runtime; cost (tokens per protocol); and the separate contribution of the critic (findings rejected or downgraded by the critic, and how many of those were indeed wrong).

**Lessons from the first live comparison (16 October 2026, synthetic cases only).** Matching findings by exact category string is too coarse: the LLM uses generic categories where the rules use specific ones, and many "extra" LLM findings were real but unlabeled. Before Checkpoint 2 the evaluation will (a) match findings on meaning (category alias map or guideline reference + page), (b) score verified findings as the system's claims and count unverified ones separately, and (c) label real protocols with all defensible findings, including those only an LLM can see.

## 3. Data and Fallback Plan

**Sources.** Publicly available English-language clinical trial protocol PDFs and structured study metadata from ClinicalTrials.gov (API v2), retrieved by NCT ID.

**Planned scope.** 10 to 15 initial protocols divided between development and evaluation; a labeled set of findings including documented synthetic test scenarios. Two synthetic protocols (one complete, one with ten documented injected deficiencies) already exist for development and tests.

**Knowledge base.** SPIRIT checklist, ICH-GCP E6(R3) key points, and an administrative intake checklist (15 items, ADMIN-CHK-01 to 15). The current files are working drafts compiled by the team; Ron verifies them against SPIRIT 2025 and the committee's official SOP before Checkpoint 2.

**Availability and permissions.** PDF availability and terms of use are checked per document. Source access is recorded with a link, study ID and document version. This verification is not yet complete.

**Fallback.** If suitable documents are insufficient, use publicly accessible protocols from PubMed Central and guideline-based synthetic cases, limiting evaluation to verifiable findings.

## 4. Architecture

![Architecture](architecture.png)

The system has **four agents** on LangGraph with a shared state ("Blackboard"):

| # | Agent | Role | Output |
|---|---|---|---|

| 1 | **Coordinator** | Single point of contact between the human coordinator and the agents. Intake: extracts protocol text per page and metadata using regex (NCT ID, version, date, PI, sponsor, phase); structures the protocol content into a categorized JSON organized by sections, preserving the original text and page references. Runs a JSON Validation Tool to verify structure, required fields, and consistency before handoff to the Administrative Review Agent. Also executes the 29 deterministic checks. Final: determines the outcome, writes the executive summary and three reports, and emails the committee coordinator. | ReviewState (structured and validated JSON), rule findings, FinalSummary, reports, email |
| 2 | **Administrative Review Agent** | Checks format and completeness against the administrative checklist and the human-approved lessons in memory; adds context findings the rules cannot see (version mismatch between pages, appendix referenced but missing, consent form in the wrong language). Evidence is verified in code. | AdminReport (accepted, checklist, findings) |
| 3 | **Scientific Review Agent** | Fetches the ClinicalTrials.gov record and compares it with the protocol; reviews against SPIRIT / ICH-GCP; detects internal contradictions between sections. On a revision request it answers each critic point and re-emits its findings. | ScientificReport (findings, registry comparison, open questions) |
| 4 | **Scientific Critic Agent** | Audits every reviewer finding. Code first (is the quote on that page? is the guideline code real?), then one verdict per finding: verified / revise / unverified / rejected, with optional severity change. Lists issues the reviewer missed. Proposes reusable lessons for human approval. | CriticReport (verdicts, missed issues, proposed memory) |

**Flow.** PDF arrives (Google Drive or email automation → FastAPI webhook, or IMAP poller) → Coordinator intake (structured protocol JSON) → JSON Validation Tool (invalid → RETURNED_ADMIN at once) → Administrative Review. If the administrative part is not 100% complete, the Coordinator finalizes immediately (decision RETURNED_ADMIN) and emails the boss; the scientific agents do not run. Otherwise Scientific Review → Scientific Critic, with at most one focused revision round, → Coordinator final → reports → email. The boss receives an email in every case.

**Design change from v1.1.** v1.1 listed a fifth agent, an Administrative Critic. The team decided to keep four agents: administrative completeness is a technical check, and automatic evidence verification in code (quote located in the PDF, guideline code valid) is deterministic, free and sufficient for it. An LLM critic is kept only for the scientific part, where judgement is needed.


**Shared State / Blackboard.** The Coordinator creates a structured, validated JSON representation of the protocol within the LangGraph ReviewState, including study metadata, original text organized by sections, and page-level references. This shared state accompanies the protocol throughout the workflow. Each agent reads the relevant information and appends its own structured review results (administrative findings, scientific findings, critic verdicts) without overwriting the original protocol data or previous agent outputs. Deterministic validation checks the JSON schema and source references before administrative review, while handoff validation checks required fields before subsequent stages. Findings include page references, verbatim quotes, guideline references, severity and verification status. The final Coordinator uses the accumulated state to determine the outcome and generate reports. The state and execution trace are persisted per run in SQLite. Implementation: findings a reviewer drops in a revision round are kept with status WITHDRAWN, every review round's report is appended to a list, and a code-level authority guard rejects any node that writes outside its permitted fields (the protocol data is writable only at intake).


**Three-layer memory.**

- *Short:* the agents' messages on the Blackboard per run (purged after 7 days).
- *Long:* lessons proposed by agents; a human approves, edits or rejects them through the API; only approved lessons are injected into prompts.
- *Historical:* every LLM call with model, tokens, duration and output, for audit, cost tracking and evaluation.

**Outputs and Reporting.** The Coordinator generates reports from the validated, accumulated ReviewState. Each report includes study metadata (protocol ID, NCT ID, title, sponsor, PI, phase, version and review date), final decision, score when applicable, and actionable findings. Each finding contains its ID, review category, severity, verification status, protocol section and page, verbatim quote, relevant guideline reference, explanation and required action. Missing metadata is flagged rather than invented. Outcomes are PASS, NEEDS_HUMAN_REVIEW, MAJOR_CONCERNS or RETURNED_ADMIN. Reports are produced as Markdown and PDF (final, administrative and, when the scientific stage ran, scientific) and emailed to the committee coordinator with the PDFs attached; the system does not grant ethical or scientific approval.


## 5. Decision Rules and the Agent's Role

**Administrative rule (decided).** The administrative part must be 100% complete. Any verified administrative finding, critical, major or minor, is written to the report and the submission is returned (RETURNED_ADMIN). Only informational notes let a submission through. The most serious items (consent form, insurance / indemnity, readable complete PDF) are listed first.


**Scientific Decision Rule (decided: Hybrid).** Any verified critical scientific finding results in MAJOR_CONCERNS regardless of score. Otherwise, the derived score determines the outcome: 90–100 PASS, 70–89 NEEDS_HUMAN_REVIEW, and 0–69 MAJOR_CONCERNS. Unverified findings require human review and prevent automatic PASS. If multiple conditions apply, MAJOR_CONCERNS takes precedence. Thresholds are configurable.

**Derived Score.** The score starts at 100, deducting 25 points per verified critical finding, 10 per verified major finding, and 3 per verified minor finding, with a minimum of 0. Unverified findings are excluded from deductions but remain flagged for human review. Each deduction is traceable to a finding ID. The score is used in the hybrid decision rule.


**Decisions beyond ordinary code.** Agents interpret protocol meaning, detect inconsistencies across sections, and determine context-dependent checks. The Coordinator routes and bounds re-checks. The Scientific Critic verifies evidence and challenges insufficiently supported conclusions. Deterministic checks remain in code.

**Agent Guardrails and Decision Authority.** Each agent has a restricted role, tool access and permitted ReviewState fields. The Coordinator manages intake, routing, validation, reporting and applies predefined decision rules; it cannot independently judge scientific validity, alter reviewer findings or override validation failures. The Administrative Agent checks submission completeness only. The Scientific Reviewer identifies potential scientific issues, while the Scientific Critic independently verifies evidence and evaluates findings. Original protocol data is immutable. Deterministic code enforces schema validation, handoff conditions, bounded revisions and decision thresholds. All decisions are traceable, and final professional approval remains human.


**Tools.** PyMuPDF for text extraction; regex metadata; 29 deterministic checks (administrative 14, scientific 12, registry 3); ClinicalTrials.gov API v2 client; knowledge-base loader with keyword retrieval; fuzzy quote verifier; Anthropic SDK with structured outputs (every agent returns a validated schema); LangGraph for state, handoffs and conditional routing; FastAPI webhooks; SMTP; SQLite.

**Failure handling.** Invalid structured output is retried once with the error; model refusals are handled with server-side fallbacks; an LLM failure degrades to deterministic results and is listed in the report; a finding whose quote is not located in the PDF is never verified, whatever the critic says; the revision loop is bounded; anything still open at finalisation becomes UNVERIFIED and goes to a human; a full trace is kept.

## 6. Risks and Reduced-Scope Version

- **No professional ground truth.** Public protocols may not contain verified findings. Mitigation: labeled test cases, documented synthetic errors, professional validation where feasible.
- **Incorrect or unsupported findings.** LLMs may misinterpret documents or invent details. Mitigation: required citations verified in code, knowledge-base codes validated, independent scientific critic, human review of unverified conclusions.
- **No measurable multi-agent benefit.** The first synthetic comparison could not separate the single agent from the multi-agent system on F1; the multi-agent system costs about five times more (≈110k vs ≈20k tokens per protocol) and its added value is the verification layer. Mitigation: the Checkpoint 2 evaluation measures verified-only precision and the critic's contribution, not raw F1 alone.
- **Draft knowledge base.** Mitigation: verification against SPIRIT 2025 and the committee SOP before Checkpoint 2.

**If only two weeks remain:** limit to three administrative and three scientific checks on fewer protocols, keep the four-agent architecture with one re-check round, defer knowledge-base expansion, email intake and interface work; retain findings reporting, both baselines and basic evaluation.

## 7. Milestones and Team Hats

| Date | Milestone and expected deliverable | Status |
|---|---|---|
| 4 Oct 2026 | Project Charter v1.0: problem, architecture, data, metrics, baselines. | done |
| 13 Oct 2026 | Charter v1.1 (editorial revision). | done |
| 18 Oct 2026 | **Checkpoint 1:** end-to-end pipeline (intake, extraction, checks, reports, email), Rule-Based Baseline; in addition the full four-agent workflow, Single-Agent Baseline, evaluation harness, automated tests, first live runs. Charter v1.2. | done |
| 19 Oct 2026 | Charter v1.3 implemented: structured protocol JSON + JSON Validation Tool, append-only state, PDF reports with section/page/quote/action per finding, agent authority guard, hybrid decision rule (26 automated tests). | done |
| 30 Oct 2026 | **Checkpoint 2:** verified knowledge base, real public protocols, labeled finding set, improved matching metric, one-minute recorded demo. | planned |
| 1 Nov 2026 | Pre-mentoring submission: freeze the repository, draft presentation. | planned |
| 4 Nov 2026 | Mentoring session: working system, preliminary results, feedback, gaps. | planned |
| 12 Nov 2026 | Final submission: evaluation versus both baselines, README, documented results, presentation. | planned |
| 15 / 18 Nov 2026 | Project presentation: demonstration, metrics, justification of the multi-agent design. | planned |

**Ron — Product & Data:** requirements and use cases; sourcing and verifying documents; verifying the knowledge base (SPIRIT 2025, ICH-GCP, committee SOP); preparing labeled cases; defining success metrics; assessing finding quality.

**Amir — Agent & Model:** agent architecture and tools; state and handoffs; baseline implementations; guardrails; evaluation runs.

**Shared:** integration, system testing, results analysis, code documentation, final presentation.

## 8. Changes since v1.1

| Area | v1.1 | v1.2 / v1.3 |
|---|---|---|
| Agents | five (incl. Administrative Critic) | four; administrative evidence verified in code |
| Administrative rule | not specified | 100% complete or RETURNED_ADMIN |
| Scientific rule | PASS / REVISE / UNVERIFIED | Hybrid rule adopted: verified critical findings override score thresholds; unverified findings require human review |
| Score | none | Derived score used for hybrid decision-making |
| Baselines | planned | both implemented in the repository |
| Memory | not specified | three-layer memory with human-in-the-loop approval |
| Intake / output | not specified | Drive / email automation → webhook; reports + email to the coordinator in every case |
| Evaluation | F1 vs baselines | plus verified-only precision, critic contribution, semantic matching |
| Protocol representation (v1.3) | page text | structured JSON by sections with original text and page references; JSON Validation Tool before administrative review |
| State discipline (v1.3) | implicit | append-only: withdrawn findings kept, per-round reports, authority guard per agent |
| Reports (v1.3) | Markdown | Markdown + PDF; each finding with section, page, quote, explanation, required action |


## 9. Open Decisions

1. Whether the submitter receives a copy of the administrative report on RETURNED_ADMIN (today: coordinator only).
2. Final list of administrative checklist items against the committee SOP. Owner: Ron.
