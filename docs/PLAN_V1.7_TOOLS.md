# Plan v1.7: real tools for the agents, and the mentor's findings of 8 November

**Status (13 November 2026):** M8 done: full system with Sonnet 5.5 and Haiku 5.5 on the five labeled protocols
(`reports/CP2_SUMMARY.md` section 10). Scientific recall 57% / 54% against 78% for Opus (lower in every resample); both
indistinguishable from the single Opus call; cost per protocol 0.69 / 0.09 USD against 2.11. Opus stays for the scientific
agents. Open: M2c, M3, M4, the hybrid model assignment.

**Status (12 November 2026):** M5, M6 and M7 done by Ron (`reports/CP2_SUMMARY.md` section 9): 40 unmatched verified
findings classified (31 true but unlabeled / 5 wrong / 4 cannot tell), finding-correctness column filled, business value
hypothesis written. Second human check of row 4': evidence 1 yes / 12 partly / 17 no against 1 / 5 / 24 for row 4; the gain
is administrative (code floor), not scientific (tool calling); the success criterion below (yes+partly >= 15 of 30) is not
met (13). Decision: row 4 stays the headline. Open: M2c, M3, M4, M8.

**Status (8 November 2026, evening):** steps A and B built, tested and run live the same day as rows 2', 3', 4'
(`reports/results.md`; reading in `reports/CP2_SUMMARY.md` section 8; charter v1.7). Mentor items done: M1, M2 (a, b, d),
M9, M11 (the change). Open: M2c repeat runs, M3, M4, M5, M6, M7, M8, M10 slide, M12, M13. Result in one line: the tools
moved findings from verified to unverified (4': 36 verified scientific findings instead of 112) and did not change
label-matching precision beyond noise; rows 1-4 stay the headline until Ron's second human check of row 4'.

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

## Naming of the rows after v1.7

Today rows 1 and 2 are both one model call with no tool chosen by the model: row 1 trusts the model's status, row 2 adds
the code verifier after the call. Both are therefore "Single LLM call" (charter v1.6). In v1.7 the single call gets the
same tool loop as the critic (tool 3: `search_protocol`, `get_page`, `registry_field`, `kb_lookup`, up to 6 calls, code
verification after). Only then does it become a **single agent**, and the ablation reads:

| # | v1.7 configuration | What it is |
|---|---|---|
| 1 | Single LLM call, no code verification | frozen baseline (unchanged) |
| 2 | Single LLM call + code verification | frozen baseline (unchanged, the v1.6 reference) |
| 2' | **Single agent with tool use** + code verification | one LLM that calls the tools itself; the fair baseline for row 4' |
| 3 | Multi-agent without critic (code tools) | code-only verification, as today, with tools 1-2-4-7-8 in the verifier |
| 4' | **Multi-agent with critic tool use** | the critic calls the tools itself; code verification after |

Rows 1-2 are not re-run (nothing changed for them except the shared code tools, which are reported as a re-score,
not a new run). Rows 2', 3 and 4' are run on the five labeled protocols. The comparison that answers the mentor is
2' vs 4': one agent with tools against four agents with tools.

## Suggested order

* **Step A (3 days): 1, 2, 4, 6, 8** as deterministic tools in `tools/evidence_tools.py`, wired into
  `agents/base.verify_evidence`, the critic prompt and `single_agent.apply_evidence_verification`. Unit tests for each.
* **Step B (3 days): 3**, one tool loop shared by the critic (row 4') and the single agent (row 2'), with the same code
  verification after it. MockLLM gets scripted tool calls for the tests.
* **Step C (1 day): 5 and 7**, then 9 if time allows.
* **Re-run:** rows 2', 3 and 4' on the five labeled protocols, about 75 minutes, then
  `eval/rescore.py`, then a second 30-finding human evidence check by Ron (same sampler, seed changed and documented).
* **Report:** a new ablation table next to the frozen one (kb-v1 + v1.6 code vs kb-v2 + v1.7 code), charter v1.7,
  CP2_SUMMARY section 8. Success criteria: label-matching precision of the full system >= 45% at recall >= 70%;
  human check yes+partly >= 15 of 30.

## Not in scope

Changing the labels, the matching rule, the decision rule or the 29 existing checks' logic; any change to the frozen
results of 29 October (they stay as the v1.6 baseline).

## Mentor's comments (mentoring session, 8 November 2026) and the planned response

Transcript of the session (voice note) summarised; nothing below is implemented yet. Priority: **P0** = before the final
submission (12 Nov), **P1** = before the presentation (15/18 Nov) if time allows, **P2** = after.

### What she called strengths (keep, and say so on the slides)
- Boundaries: the system supports the decision and never takes it; a finding whose quote is not in the PDF is never
  verified; labels restricted to objective, text-verifiable findings.
- The comparison is built right: four configurations, same set, same matching rule, a JSON that lets anyone recompute
  the scores (she recomputed all eight rows herself).
- Research honesty: differences between adjacent rows called noise, the raw table kept before the label correction, every
  change documented. "This comes from a way of thinking, not from code."
- Real guardrails in code; the evaluation gate bypass after 18 of 19 protocols stopped at the gate.
- A straight answer to "who is really an agent" (the coordinator is an orchestrator) instead of inflating the count.
- 52 automated tests.

### Findings to fix or answer

| # | Comment | Priority | Planned response | Effort / owner |
|---|---|---|---|---|
| M1 | **An LLM failure can end in PASS.** She ran the synthetic protocol with an invalid API key: zero LLM calls, decision PASS, summary says the protocol was reviewed. Cause: `agents/administrative.py` line 74, `accepted_by_llm = report.accepted if report is not None else True`; `errors` never reach the decision. | **P0** | Rule in `scoring.hybrid_decision` / `finalize_node`: if any agent failed (`state["errors"]` non-empty) or the administrative report is missing, the decision is **NEEDS_HUMAN_REVIEW** at most, never PASS; the summary, the report and the email state which agent did not run; a run with an LLM error is marked `status="done_with_errors"` in the DB and the dashboard shows it. Tests: invalid key -> no LLM -> NEEDS_HUMAN_REVIEW + "agent did not run" in the summary. Same for the single call. | 0.5 day, Amir |
| M2 | **Which baseline, and is the gap noise?** vs row 2 the gap is 10.6 pp (all-domain, before the 4 Nov fix); vs row 1 (same model call, another sample) it is 4 pp all-domain / 5.1 pp scientific. Her bootstrap over the five protocols: the CI of the scientific gap vs row 1 includes zero. "Why did you not compare to row 1?" | **P0** | (a) `eval/bootstrap.py`: protocol-level bootstrap (and leave-one-out) CIs for precision, recall and the gaps row 4 vs row 1, vs row 2, vs row 3, both views; printed into `results.md`. (b) Report the gap against **both** baselines and state which one each claim holds against. (c) Repeat-run experiment: the same PDF twice on configurations 1, 2 and 4 (one protocol, ~700k input tokens) to measure run-to-run variation directly; report the spread. (d) One slide: "how do we know it is not noise". Honest expected outcome: recall gap (+32 pp) survives, precision gap does not with n=5. | 1 day, Amir (code) + 1 day runs |
| M3 | **Average over more protocols and look at outliers.** Run the four configurations on the 16-19 protocols, compare averages, find extreme values and understand them. | P1 | Rows 1-4 on the 11 unlabeled evaluation protocols (cost ~ 4 x 11 runs: about 16M input tokens for row 4 alone; decide the budget). Without labels: counts, unverified rate, decision, cost per protocol, and outlier detection (a protocol whose numbers differ by > 2 SD from the mean) with a short explanation per outlier. | 1 day code + run time + budget; Amir |
| M4 | **Deterministic rules counted as verified where they are noisy.** | **P0** | Audit of the 29 rules on the five labeled protocols: for every rule finding, did Ron's label set or her human check agree? Rules with a false-positive history (e.g. the contents-page quotes, sample-size regex) become `unverified` or `info`, or are fixed (plan tool 6); the audit table goes into the report. The decision rule is unchanged. | 1 day, Amir + Ron |
| M5 | **77% of verified findings do not match a label. Are they wrong?** "Too much; explain, investigate, improve." | **P0** (explain) / P2 (improve) | Ron classifies a stratified sample of 40 unmatched verified findings (scientific, full system) into: true and unlabeled / duplicate of a matched one / wrong / evidence too weak to tell. Result on one slide next to the 1/5/24 check. The "improve" part is this plan's tools 1-8. | 1 day, Ron |
| M6 | **The human-check question was not the right one.** The sheet asks whether the quote supports the finding; the committee cares whether the finding is a real problem. | P1 | Second column on the same 30 rows: "is the finding itself correct, regardless of the quote?" (yes / partly / no / cannot tell). Reported as two numbers: evidence quality (1/5/24) and finding correctness (to fill). | 2 hours, Ron |
| M7 | **Business value is weak.** Quantify the pain in time and money (the KPI); make the trade-off decision explicitly: "this costs 6x and we need it because quality goes from X to Y". | **P0** | Ron collects from the committee coordinators: minutes per protocol for the administrative check and for the scientific pre-read, protocols per month, cost of a returned-incomplete cycle. System side: 8 min and ~USD 2 per protocol for the full system, ~1.5 min and ~USD 0.3 for the single call (compute from the saved token counts and list prices). One slide with the two tiers and the decision rule: single call for triage, full system for what reaches the committee; recall 78% vs 46% is the reason. | 1 day, Ron (data) + 0.5 day Amir (numbers) |
| M8 | **Why Opus?** Do the model research, even retroactively; explain every choice as a trade-off. | P1 | Row 4 (and row 2) on two labeled protocols with `claude-sonnet-5-5`, same settings; precision/recall/cost side by side; one slide "model choice". If Sonnet is close, the recommendation changes. | 0.5 day + ~1.2M input tokens, Amir |
| M9 | **Why not deterministic only?** | **P0** (one slide) | Add row 0 "rules only" to the table from the saved outputs (the rule findings are in every run): scientific recall 1/37, 16 rule findings over five protocols; administrative completeness is where the rules shine (that is the gate). The slide: rules give the gate, the LLM gives the scientific recall. | 0.5 day, Amir (rescore option) |
| M10 | **Did you change labels after seeing the results?** | **P0** (answer) | The exact answer, on a slide: the domain field of 16 labels was changed on 30 Oct, after the run, before the labeler saw any system output, with her written approval; text, quote, category, severity, page untouched; originals in `domain_original` and commit 545a516; the raw table is kept and both are reported. No other label was touched. | 0, written |
| M11 | **Which agent chooses a tool or decides the next step?** | **P0** (answer) / P2 (change) | Today: none; routing and tools are code (agentic workflow, evaluator-optimizer pattern). Plan v1.7 above gives the critic and the single agent a tool loop; until then the answer is the honest one. | 0 / plan |
| M12 | **How much time does the system save the coordinator?** | **P0** (answer) | From M7. If no committee data arrives in time: an estimate from the five protocols (pages read vs findings to check), labelled as an estimate. | with M7 |
| M13 | **Product / POC / MVP.** "Get to a product; explain every choice." | P2 | After the course: hosted instance, committee pilot on 10 protocols with the coordinators' feedback as the next label set. | later |

**Status of the table above (8 November, evening).** M1 done (`agent_failures`, decision capped, tests). M2 (a) and (b) done
(`eval/rescore.py --bootstrap`, gaps against rows 1, 2 and 3 and between the tool-use rows), (d) the slide is to write,
(c) repeat runs not run. M9 done (row 0). M11: the change is done (rows 2', 3', 4'), the answer is now "in the tool-use
rows the reviewer, the critic and the single agent choose their tools; routing and the decision rule stay in code".
M4, M5, M6, M7, M8, M3, M12, M13 unchanged.

### Prepared answers (the mentor's list, to rehearse)
1. Full system at 6x tokens: two tiers; recall 78% vs 46%; USD 2 vs 0.3 per protocol vs hours of a coordinator (M7).
2. Which agent chooses a tool: none today, by design; v1.7 plan (M11).
3. 77% unmatched: label scope (9 vs 37 per protocol), the human check, the M5 classification; improvement = tools 1-8.
4. Noise: bootstrap CIs, repeat runs, both baselines (M2).
5. Which API fails mid-run: the LLM call; today it can end in PASS, fixed by M1; ClinicalTrials.gov failure already becomes a finding (REGISTRY_NOT_FOUND).
6. Labels changed after results: M10, word for word.
7. Time saved: M7 / M12.
8. Why not deterministic only: row 0, recall 1/37 (M9).

### Order for the four days before 12 November
Day 1: M1 (fix + tests) and M9 (row 0). Day 2: M2 code (bootstrap, both baselines) and the repeat runs. Day 3: M4 rule
audit (Amir) while Ron does M5 and M7 data. Day 4: slides for M2, M5, M7, M9, M10; charter v1.7; freeze. M3, M6, M8 only
if a day is left; the tools of this plan after the submission.
