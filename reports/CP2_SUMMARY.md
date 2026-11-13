# Checkpoint 2 - evaluation on real protocols: what the numbers say

Companion to `reports/results.md` (generated) - this file is the team's reading of the run of 29 October 2026
(`eval/results/ablation-20261029-205913.json`, model `claude-opus-5-5`, knowledge base kb-v1, five blind-labeled public
protocols, 46 labels, all four ablation rows with the gate bypass). Re-scored views are produced by `eval/rescore.py`
from the saved findings; the LLM outputs were produced once. The tables below are the re-score of **4 November 2026**:
the labeler's domain correction of 30 October (section 2.3) plus the sub-item guideline-code correction of the code-only
rows (section 2.5). The raw table of the live run, scored with the labels as first delivered, is kept in
`eval/results/results_live_raw_20261029-205913.md`; the 30 October re-score in
`eval/results/rescore-20261029-205913-20261101-112300.json`.

Updated 4 November 2026 after Ron's deliverables (knowledge base kb-v2, filled 30-finding human check,
`reports/EVALUATION_AND_LIMITATIONS.md`, `reports/ABLATION_ANALYSIS.md`, `docs/CHARTER_CONSISTENCY_AUDIT.md`).
Updated 8 November 2026 after the mentoring session: section 8 (row 0, bootstrap uncertainty, and the v1.7 tool-use rows
2', 3', 4' run the same day). Sections 1-6 describe the frozen rows 1-4 and are unchanged.
Updated 13 November 2026: section 10, the model comparison (full system with Sonnet 5.5 and Haiku 5.5, mentor M8), and
section 10.5, the hybrid assignment (Opus for the scientific agents, Sonnet for the other two): recall 89% / 80%.
Updated 12 November 2026: section 9, Ron's second round of human evaluation (finding correctness on the 30 findings of
4 November, 30 findings of row 4', 40 unmatched verified findings) and the business value hypothesis.

## 1. Headline numbers

| View | Row | Precision of verified | Recall of labels | Unverified | Tokens in | Runtime |
|---|---|---|---|---|---|---|
| charter (all domains) | 2 Single LLM call + verification (baseline) | 18% (21/120) | 46% (21/46) | 3 | 207k | 568 s |
| charter (all domains) | 4 Full system | 23% (43/184) | 74% (34/46) | 51 | 1,280k | 2,372 s |
| scientific only (37 labels) | 2 Single LLM call + verification (baseline) | 25% (17/68) | 46% (17/37) | 0 | - | - |
| scientific only (37 labels) | 4 Full system | **34% (38/112)** | **78% (29/37)** | 50 | - | - |

Before the 4 November correction row 2 read 13% / 46% (all domains) and 18% / 46% (scientific); row 4 is unchanged.
Row 0 (rules only) and the v1.7 rows 2', 3', 4' of 8 November are in section 8; they do not change this headline.

Against the charter targets:

* **Recall of labeled findings >= 0.80: narrowly missed** on the scientific view (78%, 29 of 37; one more match would
  reach it); 74% on the all-domain view. The eight misses are all generic `OTHER` labels (section 3).
* **Precision of verified findings >= 0.80: not met** (23% / 34%). Section 2 explains what this number measures;
  section 2b gives the human evidence check, which is lower still.
* **+5 pp precision over the Single LLM call baseline at equal or better recall: met** (+5 pp all-domain, +9 pp scientific;
  recall +28 pp / +32 pp). The margin is smaller than reported on 30 October (+10 / +16) because the baseline was
  under-scored by the sub-item code bug (section 2.5).
* **Human check of 30 verified findings (cited passage supports the finding): not met.** 1 yes, 5 partly, 24 no
  (section 2b).
* **Cost:** the full system uses ~6x the input tokens and ~4x the runtime of the single agent per protocol.

## 2. Why precision is low, and what it does and does not mean

1. **The system reports far more than the labeler recorded.** Ron labeled about 9 findings per protocol, restricted by
   design to objective, text-verifiable issues. The full system verifies about 37 per protocol. Every verified finding
   that matches no label counts as a false positive, whether it is wrong or merely unlabeled. Label-matching precision
   therefore measures agreement with a deliberately narrow label set; it says nothing about whether the unlabeled
   findings are right. **The 30 October claim that it is a "lower bound on the true precision" is withdrawn:** the human
   evidence check (section 2b) shows that most sampled verified findings are not supported by their own quote, so the
   true precision cannot be assumed to be higher than the label-matching number.
2. **Administrative package completeness.** Public registry protocols have no consent form, insurance statement,
   signature page or sponsor declaration. The rules and the administrative agent correctly report those absences
   (verified by construction) and the labeler, by the reduced-scope plan, did not label them: 28 of the 72 verified
   administrative findings are of this kind (consent, insurance, signature page, sponsor, ethics statement, referenced
   documents). The scientific-only view removes this artefact. As Ron's analysis states, absence in a public PDF is not
   proof of absence in the hospital submission package.
3. **Domain classification of 16 labels (corrected 30 October).** Sixteen labels on data management, monitoring,
   amendments, confidentiality and the consent process (SPIRIT-26/29/31/32/33) were first recorded as *administrative*;
   the system raises the same issues through the scientific reviewer (e.g. INVEST: `SCI-L015` "Monitoring plan and
   amendment communication lack detail", SPIRIT-29/31, page 27, is label #1 + #3 of that protocol), so under the
   domain-first rule they could not match. The labeler agreed in writing to move the domain of those 16 findings to
   *scientific* - the domain field only; text, quote, category, severity and page untouched, the original value kept
   in `domain_original`, the untouched files in commit `545a516`. The decision was taken before the labeler saw any
   system output; the tables were rebuilt with `eval/rescore.py` (no new LLM calls). Effect on the full system:
   all-domain recall 61% -> 74%, scientific recall 90% (19/21) -> 78% (29/37) because the scientific label set grew
   from 21 to 37 and the system missed 8 of the 16 moved labels' neighbours. The `expected_decision` stays
   RETURNED_ADMIN for every protocol: the decision is the production rule applied to the real document (which lacks
   consent, insurance and signature documents), not a function of the labels.
4. **Generic-category labels.** 60% of the labels are OTHER / INTERNAL_CONTRADICTION / METHOD_UNSPECIFIED. The v1.5
   matching amendment (page required for generic categories) keeps one generic prediction from matching every such
   label at once; it makes the scores more conservative.
5. **Sub-item guideline-code bug (found 4 November, fixed the same day).** `verify_evidence` (`agents/base.py`) read the
   guideline reference with a character class that accepted only upper-case sub-item letters, while the knowledge base
   spells them in lower case: `SPIRIT-27b` was cut to `SPIRIT-27`, an unknown code, and the finding failed the
   "guideline code valid" check. In the two rows whose status is decided by code alone this demoted correctly cited
   findings to *unverified*: 18 of 21 unverified findings in row 2 and 24 of 33 in row 3. The bug was masked for the
   codes that the kb-v1 compatibility list still carried bare (`SPIRIT-14`, `-21`, ...) and surfaced when Ron's kb-v2
   removed that list and three tests failed. Fix: one character class plus a regression test
   (`tests/test_evidence_codes.py`). The rows were re-scored from the saved evidence checks against the kb-v1 code set
   (`eval/rescore.py --kb-codes eval/results/kb-v1-codes.json`; the saved outputs are not modified, the correction is
   applied in memory and recorded in the results header):

   | Row | Precision (scientific) | Precision (all) | Unverified (all) | Recall |
   |---|---|---|---|---|
   | 2 Single agent + verification | 18% -> **25%** (17/68) | 13% -> **18%** (21/120) | 21 -> 3 | unchanged |
   | 3 Full system without critic | 26% -> **33%** (26/79) | 15% -> **20%** (30/150) | 33 -> 9 | unchanged |
   | 4 Full system | 34% (1 finding affected; the critic's verdict stands) | 23% | 51 | unchanged |

   Consequence for the reading: the critic's contribution to *precision* disappears (row 3 vs row 4: 33% vs 34%);
   its measured contribution is recall and routing (section 3).

## 2b. Human evidence check of 30 verified findings (Ron, completed 4 November 2026)

`eval/make_human_check.py` sampled 30 *verified* findings of the full system (row 4), six per protocol, seed fixed
(`eval/human_check/verified_findings_check.csv`). Ron checked each quote on the physical PDF page with its context,
without reading the system's explanation first, and answered one question: does the cited passage support the flagged
issue under the cited guideline item? Summary in `eval/human_check/HUMAN_CHECK_SUMMARY.md`.

| | yes | partly | no |
|---|---|---|---|
| all 30 | 1 (3%) | 5 (17%) | 24 (80%) |
| scientific findings (20) | 0 | 4 | 16 |
| administrative findings (10) | 1 | 1 | 8 |
| LLM findings (27) | 1 | 5 | 21 |
| rule findings (3) | 0 | 0 | 3 |

By category of the 24 "no": METHOD_UNSPECIFIED 6, FORMAT_ISSUE 4, INTERNAL_CONTRADICTION 3, SAFETY_GAP 2,
MISSING_DOCUMENT 2, one each of CONSENT_GAP, ETHICS_GAP, MISSING_SECTION, INCONSISTENT_PHASE, INCONSISTENT_SAMPLE_SIZE,
REGISTRY_MISMATCH, OTHER.

What the failures look like (Ron's notes, paraphrased):

* The quote documents that the topic *exists* in the protocol, not that it is deficient: a "no DSMB" finding quoting the
  sentence that mentions the DSMB; a "version missing" finding quoting the version date.
* The quote is a table-of-contents line or is cut mid-sentence. All three rule findings in the sample fail this way:
  the deterministic check fired on real numbers (two sample sizes, two phases, enrollment vs registry) but the evidence
  text that `checks._context` attached came from the contents page or a figure caption. The finding is defensible, the
  evidence shown is not (charter v1.6, open decision 8).
* The guideline item does not match the claim (SPIRIT-8 dissemination cited for a phase inconsistency).
* RCT-only SPIRIT expectations applied to observational or retrospective designs (ALK digital pathology).

What it means. `verified` in this system means: the quote was located in the PDF, the guideline code exists, and the
critic (row 4) agreed. It does not mean the claim is supported by the quote. On this sample the chain locates text
reliably and judges relevance poorly. The two numbers of this checkpoint therefore describe different failures and are
reported side by side: label-matching precision (34%) says how often a verified finding coincides with the labeler's
narrow label set; the evidence check (3% yes, 20% yes-or-partly) says how often the cited passage actually carries the
claim. Neither can be used to argue that the other is pessimistic.

Consequences drawn: (1) the "precision is a lower bound" reading is withdrawn everywhere (charter v1.6, this file,
demo); (2) the system is presented as a traceable pre-review prototype whose every finding needs a human reader, not as
a verifier; (3) the next engineering step is evidence quality, not more agents: absence search over the whole protocol
for "missing" claims, duplicate detection, per-finding registry checks, a numbers table, and rebuilt evidence text for
rule findings (section 7).

## 3. What the multi-agent design buys (mentor question: "5x cost for a few points - what do you recommend?")

![The four configurations](../docs/ablation_configs.png)

*`docs/ablation_configs.png` (source `docs/ablation_configs.html`): the same pipeline in the four frozen rows of the ablation; grey dashed boxes are absent in that configuration; the red dashed path is the production behaviour of the administrative gate, bypassed in evaluation runs; the blue dashed arrow is the revision round. The tool-use rows of section 8 are the same pipeline with a tool loop inside the single call (2'), the reviewer (3') or the reviewer and the critic (4').*

* **Recall.** On the scientific view the full system reaches 78% of the labeled findings (29/37) against 46% for the
  single agent with the same verification. Per protocol: ABC PICU 7/8, SAFER 7/7, INVEST 7/9, fetal cardiac 5/8,
  ALK 3/5. All eight misses are generic `OTHER` labels (data-transfer controls, de-identification timing, consent-role
  wording, missing-value handling, image standardisation): the reviewer either did not raise them or raised them from
  a different page than the labeler quoted (the v1.5 page requirement then counts a miss).
* **Critic.** After the sub-item correction, rows 3 and 4 have the same label-matching precision (33% vs 34%): the
  critic does not filter better than the code check on this set. Its measured contributions are (a) the revision round,
  which lifted scientific recall from 57% (row 3) to 78% (row 4); (b) routing: 50 scientific findings sent to a human
  as unverified instead of 9, and 36 critic-raised issues that are never scored; (c) 3 findings rejected or withdrawn.
  The human evidence check shows that routing is the right direction: most verified findings still need a reader.
  Rows 3 and 4 differ by the critic *and* the revision round together; the design does not isolate the verdicting
  alone (Ron's ablation analysis, point 3).
* **Verification layer.** In row 2, after the correction, 3 of the single agent's 123 findings could not be located in
  the PDF or cited an unknown guideline code and were demoted to unverified (21 before the fix). Rows 1 and 2 are two
  separate model calls, not one output scored twice, so the difference between them (precision 29% -> 25%, recall
  57% -> 46%) mixes the effect of verification with run-to-run variation of the model; a few points between adjacent
  rows are within that noise, the 32-point recall gap between rows 2 and 4 is not.
* **Recommendation (tiered).** Default: single LLM call + code verification (row 2) for triage at ~1/6 of the cost;
  full system with the critic for protocols that reach the committee (anything not RETURNED_ADMIN, or on request),
  where recall matters more than cost. The administrative gate stays deterministic in both tiers. In both tiers every
  finding, verified or not, is read by a person before it reaches the committee.

## 4. Mentor question: "which of the four is really an agent?"

The Coordinator is an orchestrator (intake, validation, routing, decision rule, reports); it makes no judgement
calls. The Administrative Review Agent, the Scientific Reviewer and the Scientific Critic are LLM agents with a role,
tools, a bounded authority on the shared state and structured outputs; the critic is the only one that argues with
another agent (one revision round). We say so in the presentation rather than inflating the count.

A related question, "why do the agents not call tools themselves": the tools (PDF parsing, the 29 rules, the registry
lookup, the quote and code checks) run in code around each LLM call, always, so verification cannot be skipped by the
model and every row of the ablation has a fixed number of calls. LLM tool calling (the model asking for a page or a
search) was built on 8 November (v1.7) and run as rows 2', 3', 4' (section 8): there the single call, the reviewer and
the critic choose their own tool calls (113 calls over 15 runs), so by the strict definition those rows are agents;
routing between agents and the decision rule stay in code in every row.

## 5. Limitations to state plainly

* Five protocols, 46 labels, one annotator, no clinical expert adjudication (Sheba's internal comments were not
  released; the research-authority professor was unavailable). Labels are objective text-level findings only.
* Findings that need clinical judgement are not labeled; when the system reports them they are presented as
  "requires expert verification", never as verified claims.
* The 30-finding human evidence check (section 2b) found the cited passage supporting the finding in 1 of 30, partly in
  5. `verified` is a traceability status, not a correctness guarantee.
* One run per configuration (no repeats); differences of a few points between rows are not significant. Since
  8 November every row carries a protocol-level bootstrap interval (section 8); run-to-run variation of the model is
  still not separated from protocol variation.
* The matching rule was amended for generic categories on 29 October before the run (documented, conservative).
* The domain of 16 labels was corrected after the run but before the labeler saw any output (section 2.3); the raw
  table with the labels as first delivered is kept next to the re-scored one.
* The sub-item guideline-code bug (section 2.5) affected the code-only rows until 4 November; the correction is a
  deterministic re-score, documented in `reports/results.md` and in the charter (v1.6).
* The evidence text attached to rule findings can come from the contents page (section 2b); fixing it changes every
  row and needs a new run.
* Rows 1-4 were produced with knowledge base kb-v1 and the v1.6 code; rows 2', 3', 4' (section 8) with kb-v2 and the
  v1.7 code, eight days later. A difference between a primed and an unprimed row therefore mixes the tools, the
  knowledge base and run-to-run variation.

## 6. Reproducing

```
python eval/protocols/fetch_protocols.py            # PDFs from ClinicalTrials.gov
python eval/ablation.py --cases-glob "nct*.json"    # live run, ~75 min, ~USD 10 (writes reports/results.md)
python eval/rescore.py --stamp <stamp> --kb-codes eval/results/kb-v1-codes.json   # rebuild the tables from the saved findings, no LLM calls
python eval/make_human_check.py --stamp <stamp>     # 30-finding sheet for the human check
```

## 7. Evidence tools for the agents (planned 1 November, built 8 November as v1.7; results in section 8)

Decided on 1 November: no change to the agents before 12 November. Reversed on 8 November after the mentoring session
(the mentor's point: a model that chooses no tool is not an agent). The tools below were built the same day as
deterministic evidence tools for every configuration plus LLM tool calling, and run as rows 2', 3', 4' next to the
frozen rows (section 8). The ranked list as planned:

| Tool | Agent | Problem it addresses | Evidence |
|---|---|---|---|
| absence search over the whole protocol (keywords per category, model-proposed synonyms) | critic, administrative | "missing X" findings whose quote only shows that X is mentioned; most of the 24 "no" | section 2b |
| duplicate / overlap detection against other findings and rule findings | critic | the same issue reported two or three times inflates the verified count | section 2 |
| per-finding registry field check (enrollment, phase, outcomes) | critic, reviewer | REGISTRY_MISMATCH judged from prose | section 2b |
| numbers and dates table built once at intake | all | internal contradictions across distant pages | ContraDoc, FIND |
| rebuilt evidence text for rule findings | coordinator | contents-page quotes | section 2b |
| protocol search on demand (LLM tool calling, PaperQA2-style evidence gathering) | critic, then reviewer | 60-75k input tokens per call | PaperQA2 |

Literature behind the direction: CRITIC (Gou et al., ICLR 2024: self-critique without tool feedback is unreliable, with
tools it works), Agent-as-a-Judge (Zhuge et al., 2024: a judge with tools agrees with humans 90% vs 70%), PowerGPT
(2025 RCT: keep the LLM out of the arithmetic). Rows 1-4 stay frozen; the tool-use configurations are reported as new
rows, never as a re-run of row 4.

## 8. v1.7 (8 November 2026): row 0, uncertainty, and agents with tool use

Context: mentoring session of 8 November (findings M1-M13 with priorities in `docs/PLAN_V1.7_TOOLS.md`). Built,
tested (65 automated tests) and run the same day:

* **M1, agent failure.** The mentor ran the synthetic protocol with an invalid API key: zero LLM calls, decision PASS.
  Now any agent that did not run caps the decision at NEEDS_HUMAN_REVIEW, the summary opens with a warning naming the
  agent, and `agent_failures` is stored with the run and shown on the dashboard. Same rule in the single call.
* **M9, row 0.** Rules only, computed from the rule findings saved with every run: scientific precision 6% (1/16),
  recall 3% (1 of 37 labels); all-domain 9% / 9%. The rules give the administrative gate; the scientific recall comes
  from the LLM.
* **M2, uncertainty.** Protocol-level bootstrap (five protocols resampled with replacement, B = 2000, seed 20261108):
  95% interval per row and, for every gap, the mean, the interval and P(gap <= 0). Gaps are reported against both
  baselines (rows 1 and 2) and against row 3.
* **Evidence tools (code floor, every configuration).** Numbers table and study design built at intake and given to
  every agent; absence search over the whole protocol for "missing X" claims; mention-is-not-evidence rule;
  category-to-guideline-code fit; duplicate merge (rejected, not deleted); full-sentence rule quotes that skip the
  contents page. The critic can demote a finding but cannot verify one the code demoted.
* **Tool calling (`tool_use`).** The reviewer (`search_protocol`, `get_page`, `get_section`, `kb_lookup`,
  `power_calc`), the critic (same, with `registry_field` instead of `power_calc`) and the single agent (all six) call
  the tools themselves, at most six calls per LLM call; the deterministic verification runs after the loop.

Run: `eval/ablation.py --only single_tools agents_no_critic_tools agents_full_tools --cases-glob "nct*.json"`,
stamp `20261108-154153`, model `claude-opus-5-5`, knowledge base kb-v2, 15 reviews, 57 minutes, 5.4M input tokens.
Merged with the frozen run by `eval/rescore.py --stamp 20261029-205913,20261108-154153 --kb-codes
eval/results/kb-v1-codes.json` into the eight-row `reports/results.md`.

### 8.1 The eight rows (scientific view, 37 labels)

| Row | Precision of verified | Recall of labels | Unverified (scientific) | Tokens in | Runtime |
|---|---|---|---|---|---|
| 0 Rules only | 6% (1/16) | 3% (1/37) | 0 | 0 | 0 s |
| 1 Single LLM call, no code verification | 29% (19/66) | 57% (21/37) | 0 | 207k | 548 s |
| 2 Single LLM call + code verification | 25% (17/68) | 46% (17/37) | 0 | 207k | 568 s |
| 2' Single agent with tool use + code verification | 29% (7/24) | 49% (18/37) | 33 | 729k | 882 s |
| 3 Full system without the critic | 33% (26/79) | 57% (21/37) | 9 | 453k | 918 s |
| 3' Full system without the critic, reviewer with tool use | 31% (9/29) | 65% (24/37) | 47 | 1,043k | 1,190 s |
| 4 Full system | 34% (38/112) | 78% (29/37) | 50 | 1,280k | 2,372 s |
| 4' Full system, reviewer and critic with tool use | 36% (13/36) | 70% (26/37) | 113 | 3,655k | 3,418 s |

All-domain view (46 labels): 2' 18% (10/57) / 46%; 3' 17% (12/70) / 59%; 4' 21% (17/80) / 65% (full tables,
intervals and per-case rows in `reports/results.md`).

### 8.2 What the agents did with the tools

113 tool calls over the 15 runs: 2' 19 (search_protocol 14, power_calc 4, registry_field 1); 3' 28 (search 24,
power_calc 4); 4' 66 (reviewer 46: search 39, power_calc 6, kb_lookup 1; critic 20: search 19, registry_field 1).
`get_page` and `get_section` were never called: the agents already receive the whole protocol in the prompt, so the
tool they reach for is the search before a "missing X" claim, and the sample-size calculator. Every call and its
result are stored with the LLM interaction (`_tool_calls`) and shown on the dashboard.

The code floor did most of the demoting. Of the unverified findings (both domains) in the new rows, the absence
search accounts for 39 (2'), 66 (3') and 85 (4'); the mention-only rule for 3 / 3 / 7; a quote not located for
5 / 10 / 6; in 4' another 39 came from the critic's own verdicts and 8 from "no revision round left".

Label-matched share by status (scientific findings, critic-raised issues excluded):

| Row | verified (matched) | unverified (matched) |
|---|---|---|
| 4 Full system | 112 (38) = 34% | 14 (3) = 21% |
| 2' | 24 (7) = 29% | 33 (8) = 24% |
| 3' | 29 (9) = 31% | 47 (10) = 21% |
| 4' | 36 (13) = 36% | 74 (13) = 18% |

### 8.3 Reading

1. **Precision did not move.** Every precision gap that involves a tool-use row has an interval that includes zero:
   4' vs 4 +2 pp (-18 to +20, P = 0.38), 4' vs 2' +6 pp (-5 to +17, P = 0.13), 3' vs 3 -2 pp, 2' vs 2 +5 pp
   (P = 0.24). The success criterion written in the plan (label-matching precision >= 45% at recall >= 70%) is not met.
2. **The tools changed where findings go, not how many match a label.** Row 4' verifies 36 scientific findings instead
   of 112 and sends 113 to a human instead of 50. The demoted findings match a label less often (18%) than the
   verified ones (36%), so the floor removes mostly findings that match nothing, but it also demoted 13 matched
   findings: the recall counted on verified findings alone fell. Whether the demoted "missing X" findings are the
   kind that failed the human check (24 "no" of 30, section 2b) is exactly what label matching cannot see.
3. **Recall.** 4' reaches 70% of the labels against 78% for row 4; the gap is below zero in every resample
   (P = 1.00). 3' is above 3 (65% vs 57%) and 2' above 2 (49% vs 46%), both within noise. The tool loop makes the
   reviewer more careful and shorter: fewer candidates, fewer matches.
4. **Cost.** 4' uses 2.9x the input tokens of row 4 (3.65M vs 1.28M) and 1.4x the runtime; 2' uses 3.5x the tokens
   of row 2. Each tool round re-sends the whole conversation, protocol included.
5. **The mentor's question.** In rows 2', 3', 4' the model chooses its tools (113 calls), so these rows are agents by
   the strict definition, and the comparison she asked for exists: one agent with tools (2') against four agents
   with tools (4') gives +6 pp precision (noise) and +22 pp recall (P = 0.01) at 5x the tokens. The honest summary is
   that tool use made the system route more and claim less; it did not make its claims agree more with the labels.
6. **Headline.** Rows 1-4 stay the headline result. Row 4' becomes the headline only if the second 30-finding human
   evidence check, drawn from it with the same sampler (`eval/make_human_check.py --stamp 20261108-154153 --row
   agents_full_tools`, new seed), shows that the cited passages support the findings more often than 1 yes / 5
   partly / 24 no. That is the number the tools were built to move.

### 8.4 Still open from the mentoring session

M2c repeat runs (the same protocol twice on rows 1, 2 and 4, to measure run-to-run variation directly), M3 (the
unlabeled protocols), M4 (audit of the 29 rules against the labels), M8 (Sonnet comparison), M13 (product: a first
end-user Gradio app by Ron, `gradio_app.py`). Done on 12 November, section 9: M5 (40 unmatched verified findings
classified), M6 (finding-correctness column), M7 / M12 (business value hypothesis). M10 (the labels-changed answer) is
written. Order and owners in `docs/PLAN_V1.7_TOOLS.md`.

## 9. Human evaluation, round 2 (Ron, 12 November 2026)

Three sheets, all filled by Ron after the mentoring session; counts in `eval/human_check/HUMAN_CHECK_ROUND2_SUMMARY.md`
(generated by `eval/summarize_human_check.py`), her caveats in `eval/human_check/HUMAN_REVIEW_PRESUBMISSION_AUDIT_REVISED.md`.
The system columns of every sheet are unchanged and the blind labels were not touched. These are classifications by a
single annotator who had seen the system's output by then; they are a second layer next to the blind labels, not a
precision estimate and not a clinical adjudication.

### 9.1 Evidence support, row 4 against row 4' (the check the tools were built for)

Question, same as on 4 November: does the cited passage support the finding?

| Sample of 30 verified findings | yes | partly | no | yes or partly |
|---|---:|---:|---:|---:|
| Row 4, full system (checked 4 Nov) | 1 | 5 | 24 | 6 (20%) |
| Row 4', full system with tool use (checked 12 Nov) | 1 | 12 | 17 | 13 (43%) |
| ... scientific findings only: row 4 / row 4' | 0 / 0 | 4 / 4 | 16 / 13 | 4 of 20 / 4 of 17 |
| ... administrative findings only: row 4 / row 4' | 1 / 1 | 1 / 8 | 8 / 4 | 2 of 10 / 9 of 13 |

* The share of findings whose quote supports them at least partly doubled (20% to 43%), still with a single "yes".
  Fisher exact test on "yes or partly" against "no": p = 0.095; with 30 against 30 the difference is suggestive, not
  established. The criterion written in the plan before the check (yes or partly in at least 15 of 30) is not met (13).
* **The gain is administrative.** For scientific findings the evidence is unchanged (4 partly of 20, 4 partly of 17).
  For administrative findings it went from 2 of 10 to 9 of 13. The administrative agent has no tool calling in any
  configuration; what changed for it between the two runs is the deterministic evidence floor (absence search,
  mention-is-not-evidence, full-sentence rule quotes). So on this sample the code floor improved the evidence of
  administrative findings, and tool calling by the reviewer and the critic did not improve the evidence of scientific
  findings.
* Row 4' leaves only 42 verified findings with a cited passage over the five protocols, so 30 of them is close to a
  census; the row 4 sample is 30 of its 184 verified findings.

### 9.2 Finding correctness, regardless of the quote (mentor M6)

The mentor's point: whether the quote supports the finding is not the committee's question; whether the finding is a
real problem is. Second column on the same rows:

| Sample | yes | partly | no | cannot tell | yes or partly |
|---|---:|---:|---:|---:|---:|
| Row 4 (30) | 1 | 10 | 11 | 8 | 11 (37%) |
| Row 4' (30) | 4 | 7 | 14 | 5 | 11 (37%) |
| ... scientific: row 4 (20) / row 4' (17) | 0 / 0 | 9 / 2 | 8 / 12 | 3 / 3 | 9 of 20 / 2 of 17 |
| ... administrative: row 4 (10) / row 4' (13) | 1 / 4 | 1 / 5 | 3 / 2 | 5 / 2 | 2 of 10 / 9 of 13 |

* Overall the two rows are equal (11 of 30 each). Underneath, the administrative findings of row 4' are better (9 of
  13 at least partly correct, against 2 of 10) and its scientific findings are worse (2 of 17, against 9 of 20). After
  the code floor has sent the "missing X" claims to a human, the scientific findings that stay verified in row 4' are
  mostly contradiction and method claims, and the reviewer judged 12 of 17 of them not correct.
* Evidence and correctness are different things: of the 24 row 4 findings whose quote does not support them, 5 are
  still partly correct and 8 cannot be decided from the PDF; 11 are wrong. A finding with a bad quote is not
  necessarily a wrong finding, and it still cannot be shown to a committee as verified.
* All three rule findings in the row 4 sample have an unsupporting quote, and two of them are judged wrong (mentor
  finding M4, the audit of the 29 rules, is still open).

### 9.3 The 40 verified scientific findings that match no blind label (mentor M5)

The mentor's question: 77% of the verified findings match no label; are they wrong? `eval/make_unmatched_check.py`
sampled 40 of the 64 such findings of row 4 that cite a passage, eight per protocol; Ron classified each one.

| Classification | n | share |
|---|---:|---:|
| true but unlabeled | 31 | 78% |
| wrong | 5 | 13% |
| cannot tell (needs registry history, approvals or expert judgement) | 4 | 10% |
| duplicate of a matched finding | 0 | 0% |

* On this classification most unmatched verified findings are defensible issues outside the deliberately narrow label
  scope, not errors. Three of the five "wrong" are rule findings (all three rule findings in the sample); two are LLM
  findings.
* Five pairs were checked as possible overlaps with matched findings (`unmatched_40_reference_crosscheck.xlsx`); none
  was a full duplicate. Partial overlap inside multi-part findings is not excluded.
* Ron's audit attaches 14 review flags to the 40 rows: composite findings where not every sub-claim is supported,
  SPIRIT expectations for randomised trials applied to an observational study (fetal cardiac), a 2017 protocol read
  against SPIRIT 2025 (a retrospective reporting-gap benchmark, not a compliance verdict), a non-inferiority margin
  that needs a statistician. "true but unlabeled" means "a real gap the labels did not cover, in the reviewer's
  reading", not an adjudicated defect.

### 9.4 The two measures do not agree, and we say so

The 40-finding sheet says 78% of unmatched verified scientific findings are true; the 30-finding sheet of the same row
says 0 of 20 scientific findings are fully correct, 9 partly and 8 not. The questions differ (is this a real gap the
labels missed, against is the finding right as written), the samples differ (unmatched only, against all verified),
and it is one annotator. Five findings appear in both sheets: three get consistent answers (two rule findings wrong in
both; one true but unlabeled and partly correct) and two do not (`nct01977547 / SCI-L004`: true but unlabeled, and "no" on correctness;
`SCI-L015`: true but unlabeled, and "cannot tell"); both are among the audit's flags. We report the two results side
by side and pool nothing. Neither is a precision figure; the locked primary metric stays the label-matching precision
of section 1.

### 9.5 Decision on the headline (charter open decision 10)

Row 4 stays the headline result. Row 4' is presented as the improvement built after the mentor's comments, with what
it measurably did: it routes far more to a human (113 scientific findings instead of 50), its administrative findings
are better evidenced and more often correct, its scientific findings are not, label-matching precision is unchanged
within noise (section 8), recall is lower, and it costs 2.9x the tokens. Ron's position (10 November), which the team
adopted: keep the original four-row experiment untouched for traceability and present the tool-use version next to it.

### 9.6 Business value (mentor M7, M12)

`reports/BUSINESS_VALUE_HYPOTHESIS.md` (Ron): a team estimate of 2-3 combined staff-hours per protocol for the
administrative and preliminary scientific review, workload scenarios, and the formula for measuring net savings in a
pilot. It is stated as a hypothesis: no time saving has been measured, and the human evidence check shows that a
first-pass review with unsupported findings can add work instead of removing it.

### 9.7 Still open

M2c (repeat runs of the same protocol), M3 (the unlabeled protocols), M4 (rule audit: the rule findings fail in every
human sample so far), expert adjudication of the flagged findings, a second annotator. M8 (model comparison) was run on
13 November: section 10.

## 10. Model comparison: the full system with Sonnet 5.5 and Haiku 5.5 (13 November 2026, mentor M8)

The mentor's question: why Opus? Until this run every row used `claude-opus-5-5`, so the table said nothing about the
model. Run of 13 November (stamp `20261113-115645`): the full system (four agents, critic, one revision round, no tool
calling) on the current code and kb-v2, on the same five labeled protocols, with `claude-sonnet-5-5` (row 4-S) and
`claude-haiku-5-5` (row 4-H). Same prompts, same effort setting (medium), same output cap, same matching rule; only the
model changes. `eval/ablation.py --only agents_full_sonnet agents_full_haiku --cases-glob "nct*.json"`, merged into
`reports/results.md` by `eval/rescore.py --stamp 20261029-205913,20261108-154153,20261113-115645`.

### 10.1 Result (scientific view, 37 labels)

| Row | Model | Precision of verified | Recall of labels | Unverified | Cost per protocol | Time per protocol |
|---|---|---|---|---|---|---|
| 2 Single LLM call + code verification | Opus 5.5 | 25% (17/68) | 46% (17/37) | 0 | USD 0.43 | 114 s |
| 4 Full system (frozen, v1.6 code) | Opus 5.5 | 34% (38/112) | 78% (29/37) | 50 | USD 2.11 | 474 s |
| 4' Full system with tool use (current code) | Opus 5.5 | 36% (13/36) | 70% (26/37) | 113 | USD 4.48 | 684 s |
| 4-S Full system (current code) | Sonnet 5.5 | 23% (7/30) | 57% (21/37) | 69 | USD 0.69 | 139 s |
| 4-H Full system (current code) | Haiku 5.5 | 25% (6/24) | 54% (20/37) | 87 | USD 0.09 | 182 s |

Costs are list prices applied to the recorded tokens (Opus 4 / 20, Sonnet 2 / 10, Haiku 0.10 / 0.50 USD per million
input / output tokens). Protocol-level bootstrap (B = 2000), scientific view:

| Gap | Precision: mean (95% CI), P(gap <= 0) | Recall: mean (95% CI), P(gap <= 0) |
|---|---|---|
| 4-S vs 4 (Opus, frozen) | -10 pp (-32 to +12), P = 0.80 | **-21 pp (-26 to -12), P = 1.00** |
| 4-H vs 4 (Opus, frozen) | -9 pp (-27 to +8), P = 0.82 | **-24 pp (-46 to -6), P = 1.00** |
| 4-S vs 4' (Opus, same code) | **-12 pp (-20 to -5), P = 1.00** | -13 pp (-26 to +3), P = 0.96 |
| 4-H vs 4' (Opus, same code) | **-11 pp (-19 to -3), P = 1.00** | **-16 pp (-24 to -6), P = 1.00** |
| 4-S vs 2 (one Opus call) | -1 pp (-21 to +20), P = 0.55 | +11 pp (-3 to +25), P = 0.10 |
| 4-H vs 2 (one Opus call) | 0 pp (-14 to +14), P = 0.53 | +8 pp (-11 to +26), P = 0.24 |
| 4-S vs 4-H | -1 pp (-12 to +10), P = 0.59 | +3 pp (-16 to +24), P = 0.44 |

### 10.2 Reading

1. **The model matters for the scientific review.** With Sonnet or Haiku in all four agents the system finds 20-21 of
   the 37 labeled scientific findings instead of 29 with Opus: 21 to 24 points less recall, below zero in every resample.
   Against the Opus row on the same code (4'), precision is also lower by 11-12 points, again in every resample.
2. **Four agents on a smaller model are about one call of the larger one.** Rows 4-S and 4-H cannot be distinguished
   from row 2, the single Opus call with code verification (25% / 46%), on precision or on recall. The multi-agent
   structure does not compensate for the model.
3. **Sonnet and Haiku cannot be told apart on this set** (57% vs 54% recall, 23% vs 25% precision, intervals wide).
   Haiku's recall swings more between protocols (2 of 8 on ABC PICU, 7 of 7 on SAFER; interval 34% to 79%).
4. **Cost.** The full system costs USD 2.11 per protocol with Opus, 0.69 with Sonnet, 0.09 with Haiku. The scientific
   reviewer and the critic are 80% of the Opus cost (section 3), and they are where the recall is lost.
5. **Administrative labels: no visible difference, and too few to tell.** Of the nine administrative labels, Opus finds
   5 (row 4) and 4 (row 4'), Sonnet 3, Haiku 4. A smoke run before the comparison showed a qualitative difference:
   on the synthetic complete protocol Opus and Sonnet both noticed that the cited NCT number belongs to another trial
   and returned the submission; Haiku did not notice and let it through the gate.
6. **Reliability.** No agent failed in either run. Three scientific-reviewer answers were cut at the 16,000-token output
   cap and succeeded on the automatic retry.

### 10.3 What it means for the product

* Keep Opus for the scientific reviewer and the critic. That is where the model earns its price: the recall gap is the
   largest and the most stable difference in the whole table.
* The coordinator's model call only writes the final summary, and the administrative gate rests on the 29 rules; a
  cheaper model there (Sonnet, not Haiku, given the gate observation) was computed to save about 10% of the cost. This
  hybrid was then run and measured: section 10.5 (saving 7%, no measurable loss).
* If cost is the constraint, the choice on this evidence is not "the full system on a cheaper model": it is the single
  Opus call (row 2) at USD 0.43, or the full system on Haiku at USD 0.09, which measure the same on this set.

### 10.4 Limits

One run per model, five protocols, the label set of section 5. Rows 4-S and 4-H run on the current code (deterministic
evidence floor, kb-v2); the frozen Opus row 4 does not, so the precision comparison uses row 4' (same code, but with
tool calling). The matching Opus row without tool calling on the current code (`agents_full_v17`, row 4* in the runner)
was not run (about USD 10.5); recall is barely affected by the evidence floor, so the recall comparison against row 4
stands without it. Effort was left at `medium` for all three models; Sonnet 5.5 and Haiku 5.5 calibrate effort levels
differently from Opus, and a higher effort setting for them was not tried.

### 10.5 The hybrid assignment, measured (row 4-M, run of 13 November, stamp `20261113-125723`)

Section 10.3 computed a hybrid and did not measure it. It was run the same day: `claude-opus-5-5` for the scientific
reviewer and the critic, `claude-sonnet-5-5` for the coordinator and the administrative agent, current code, kb-v2, no
tool calling (`eval/ablation.py --only agents_full_hybrid`; the model per agent is the optional setting
`llm_agent_models`, empty by default).

| Row | Precision of verified (scientific) | Recall (scientific) | Recall (all domains) | Administrative labels found | Cost per protocol | Time per protocol |
|---|---|---|---|---|---|---|
| 4 Full system, Opus (frozen, v1.6 code) | 34% (38/112) | 78% (29/37) | 74% (34/46) | 5 of 9 | USD 2.11 | 474 s |
| 4' Full system with tool use, Opus | 36% (13/36) | 70% (26/37) | 65% (30/46) | 4 of 9 | USD 4.48 | 684 s |
| 4-S Full system, Sonnet everywhere | 23% (7/30) | 57% (21/37) | 52% (24/46) | 3 of 9 | USD 0.69 | 139 s |
| **4-M Hybrid: Opus scientific, Sonnet coordinator + administrative** | 32% (12/37) | **89% (33/37)** | **80% (37/46)** | 4 of 9 | USD 2.09 | 442 s |

Bootstrap, scientific view: 4-M vs 4-S recall +32 pp (19 to 49), P = 0.00; 4-M vs 4' recall +19 pp (0 to 38), P = 0.04;
4-M vs 4 recall +11 pp (-5 to +30), P = 0.14; precision gaps against rows 4 and 4' within noise (-2 pp and -4 pp).
Interval of row 4-M: recall 77% to 100% (scientific), 73% to 87% (all domains). No agent failed; two answers were cut at
the output cap and succeeded on retry.

Reading:

1. **Sonnet in the coordinator and the administrative agent costs nothing measurable.** Administrative labels found: 4 of
   9, as with Opus (4 and 5). The scientific recall is the highest of the table, so nothing was lost upstream either.
2. **The saving is small.** USD 2.09 per protocol; the same tokens priced on Opus alone would be USD 2.25, so the hybrid
   saves about 7% (16 cents per protocol), less than the 10% computed in 10.3, because the scientific agents wrote more in
   this run. The two agents moved to Sonnet were never where the money goes.
3. **This is, in effect, the first measured row of the product configuration**: Opus scientific agents on the current
   code, deterministic evidence floor, no tool calling. It reaches the charter's recall target for the first time
   (89% scientific, 80% all domains, target 80%). Precision of verified findings stays far from its target (32%).
4. **Tool calling is what lowered recall, not the evidence floor.** Rows 4-M and 4' share the code floor and kb-v2 and
   differ in tool calling (and in the model of the two non-scientific agents): recall 89% against 70%, P = 0.04. With
   section 9.1 (tool calling did not improve the evidence of scientific findings) and its 2.1x cost, the evidence on this
   set is against tool calling in the reviewer and the critic.

Limits, stated plainly. One run. The gain over the frozen row 4 is not distinguishable from noise (P = 0.14): the claim
that holds is "at least as good as row 4", not "better". The evidence floor and kb-v2 were developed after reading the
system's output on these same five protocols, so this is not a held-out test of the current code; the floor changes the
verification status of findings, not which findings are raised, and recall counts both, but the caveat stands. The row
mixes two changes against row 4' (no tool calling, Sonnet in two agents); the Opus-only row on the current code
(`agents_full_v17`) was still not run.
