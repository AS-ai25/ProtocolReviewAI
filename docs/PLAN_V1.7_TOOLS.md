# Plan v1.7: real tools for the agents (ranked by expected effect on the results)

**Status:** plan only, nothing implemented (decided 8 November 2026 after the mentoring session). To be extended with
the mentor's written comments. Owner of the decision: Amir and Ron.

## Why

1. **The mentor's point.** Configuration 1 is one LLM call with tool outputs pre-computed by code, so it is not an agent
   (renamed "Single LLM call baseline", charter v1.6). In configurations 2-4 the tools (PDF parser, 29 rules,
   ClinicalTrials.gov, evidence verifier, knowledge base, memory) run in code around each LLM call; the model never
   chooses a tool. By the strict definition this is an agentic workflow (orchestrator + evaluator-optimizer), not agents
   with tool use.
2. **Our own measurements.** Label-matching precision 34% (full system), and the human evidence check of 30 verified
   findings: 1 yes / 5 partly / 24 no. The 24 failures fall into five patterns (see `reports/CP2_SUMMARY.md` 2b):
   "missing X" while X exists elsewhere (about 10), a quote that mentions the topic without showing a deficiency (about 6),
   rule-finding quotes cut from the table of contents (3), guideline item that does not fit the claim (about 3),
   RCT-only SPIRIT items applied to observational designs (about 2).

Both point in the same direction: give the agents, above all the critic, tools that look at the protocol for them,
and let the model call some of them.

## Ranked list (1 = most likely to improve the results)

| # | Tool | Form | Agents | Failure pattern it addresses | Expected effect | Effort |
|---|---|---|---|---|---|---|
| 1 | **absence_search(keywords)**: search the whole protocol for the thing a "missing X" finding claims is absent (keyword list per category + synonyms the model proposes in a new optional field `absence_keywords`); returns pages and snippets | code tool, always; also callable by the critic | critic, administrative, single call | ~10 of 24 "no" | precision up, unverified down; the single biggest lever | 1 day |
| 2 | **mention-is-not-evidence rule**: a quote that contains the topic but no negation / absence / contradiction cannot support a "missing / unspecified" claim; the critic prompt says so and the code demotes such findings to unverified unless absence_search confirms the absence | code rule + prompt | critic, code-only rows | ~6 of 24 | precision up, small recall cost | 0.5 day |
| 3 | **critic tool calling**: `get_page(n)`, `search_protocol(query)`, `registry_field(name)`, `kb_lookup(code)`; the critic may call up to 6 tools before its verdict; code verification stays mandatory afterwards | LLM tool use (Anthropic tool_use loop in the critic node) | critic (row 4 only) | evidence independence: the critic can look where the reviewer did not; answers the mentor's definition | precision up moderately; tokens per call down if the full text is no longer sent | 2 days + MockLLM scripts |
| 4 | **duplicate / overlap merge**: same category + same page, or title similarity above a threshold, or overlap with a rule finding -> merge or reject | code tool, always | critic, code-only rows | inflated verified count | precision up, recall unchanged | 0.5 day |
| 5 | **study-design applicability**: intake detects the design (randomised? blinded? observational? retrospective? AI model?) from the protocol JSON; the reviewer and critic receive the list of SPIRIT items that do not apply (kb-v2 already carries the guidance) | code tool at intake | reviewer, critic | ~2 of 24 (ALK), and observational protocols in general | fewer false "missing" items | 1 day |
| 6 | **rule-finding evidence text**: `checks._context` must not cut quotes from the contents page or mid-sentence; take the full sentence around the match, skip TOC pages | code fix | coordinator (rules) | 3 of 30 (all rule findings failed on evidence text) | evidence quality; label matching unchanged | 0.5 day |
| 7 | **registry_field_check**: for REGISTRY_MISMATCH, compare the claimed field (enrollment, phase, primary outcome, intervention, sponsor) in code against the registry record | code tool, always; also callable | critic, reviewer | ~1-2 of 24 | precision; auto-verify when the code confirms | 0.5 day |
| 8 | **category -> allowed guideline codes map**: e.g. INCONSISTENT_PHASE may not cite SPIRIT-8 (dissemination); mismatch -> unverified | code rule | critic, code-only rows | ~3 of 24 | precision | 0.5 day |
| 9 | **numbers_table at intake**: every sample size, phase, version, date with its page, built once and given to reviewer and critic | code tool | reviewer, critic | internal contradictions across distant pages | recall of contradictions; evidence quality | 0.5 day |
| 10 | **reviewer tool calling** (`gather_evidence(query)`, PaperQA2-style) instead of the full protocol text | LLM tool use | reviewer | 60-75k input tokens per call | tokens down a lot; recall risk (what it does not ask for it does not see) | 2-3 days, after 3 |
| 11 | **power_calc(alpha, power, effect, sd, dropout)**: the model extracts parameters, code computes n and compares with the protocol's n | code tool, on demand | reviewer, critic | "sample size unjustified" findings without a number | evidence quality for one category | 1-2 days |
| 12 | Claude Citations API (page_location) | API feature | all | quote hallucination | not compatible with the structured outputs every agent uses; separate experiment | 1 week |
| - | self-consistency voting / repeated runs | more calls | reviewer | run-to-run noise | rewards consistency, not correctness; x3 cost. Not recommended | - |

Tools 1, 2, 4, 7, 8 also apply to the code-only rows (2 and 3) through `apply_evidence_verification`, so every row
improves and the comparison stays fair; tool 3 (and later 10) is what makes row 4 "agents with tool use".

## Suggested order

* **Step A (3 days): 1, 2, 4, 6, 8** as deterministic tools in `tools/evidence_tools.py`, wired into
  `agents/base.verify_evidence`, the critic prompt and `single_agent.apply_evidence_verification`. Unit tests for each.
* **Step B (2 days): 3**, the critic's tool loop, with the same code verification after it. MockLLM gets scripted tool
  calls for the tests. Row 4 only.
* **Step C (1 day): 5 and 7**, then 9 if time allows.
* **Re-run:** all four rows on the five labeled protocols (code tools change rows 2-3 too), about 75 minutes, then
  `eval/rescore.py`, then a second 30-finding human evidence check by Ron (same sampler, seed changed and documented).
* **Report:** a new ablation table next to the frozen one (kb-v1 + v1.6 code vs kb-v2 + v1.7 code), charter v1.7,
  CP2_SUMMARY section 8. Success criteria: label-matching precision of the full system >= 45% at recall >= 70%;
  human check yes+partly >= 15 of 30.

## Not in scope

Changing the labels, the matching rule, the decision rule or the 29 existing checks' logic; any change to the frozen
results of 29 October (they stay as the v1.6 baseline).

## Mentor's comments (to be added)

_Pending: Amir pastes the meeting notes; each comment gets a line here with the planned response._
