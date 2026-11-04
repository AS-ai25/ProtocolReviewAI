# Evaluation and Limitations - draft for final report

**BIU DS23 | Clinical Trial Protocol Review System**  
**Prepared for integration:** 4 November 2026  
**Scope:** documentary analysis of existing results; no new model run.

## Evaluation design

The repository contains 19 public ClinicalTrials.gov protocols: three development cases used for technical smoke tests and 16 evaluation cases. Five evaluation protocols have 46 blind, text-verifiable manual findings from one annotator. This restricted set is not an expert-adjudicated clinical gold standard. The 30-finding post-run human evidence check is a separate review of the full system's **verified predictions**, not a second pass on the blind labels.

All four ablation configurations use the same five cases and the evaluation-only `force_scientific` bypass, so that scientific findings remain observable despite the administrative gate. This bypass must not be described as production behaviour.

The primary metric is matched verified findings divided by all verified findings. Recall is the proportion of manual labels matched by system findings, including the project-defined verification statuses. Matching uses the locked domain-first rule and the v1.5 generic-category page constraint. This is a label-relative metric, not independently established clinical truth.

## Results: all domains (46 labels)

| Configuration | Verified precision | Label recall | Unverified | LLM calls | Input tokens | Runtime (s) |
|---|---:|---:|---:|---:|---:|---:|
| Single agent, no code verification | 23/119 (19.3%) | 25/46 (54.3%) | 0 | 5 | 207,419 | 547.9 |
| Single agent + code verification | 13/102 (12.7%) | 21/46 (45.7%) | 21 | 5 | 207,419 | 567.9 |
| Full system without the critic | 19/126 (15.1%) | 25/46 (54.3%) | 33 | 15 | 452,979 | 918.0 |
| Full system (4 agents, critic, 1 revision round) | 43/184 (23.4%) | 34/46 (73.9%) | 51 | 30 | 1,280,437 | 2,371.9 |

## Results: scientific-only view (37 labels)

| Configuration | Verified precision | Label recall | Unverified | LLM calls | Input tokens | Runtime (s) |
|---|---:|---:|---:|---:|---:|---:|
| Single agent, no code verification | 19/66 (28.8%) | 21/37 (56.8%) | 0 | 5 | 207,419 | 547.9 |
| Single agent + code verification | 9/50 (18.0%) | 17/37 (45.9%) | 18 | 5 | 207,419 | 567.9 |
| Full system without the critic | 15/57 (26.3%) | 21/37 (56.8%) | 31 | 15 | 452,979 | 918.0 |
| Full system (4 agents, critic, 1 revision round) | 38/112 (33.9%) | 29/37 (78.4%) | 50 | 30 | 1,280,437 | 2,371.9 |

For the locked baseline (single agent with code verification, row 2) versus full multi-agent system (row 4), verified precision improved from 12.7% to 23.4% (+10.7 percentage points) and label recall improved from 45.7% to 73.9% (+28.2 points) in the all-domain view. Scientific-only verified precision improved from 18.0% to 33.9% (+15.9 points), and recall from 45.9% to 78.4% (+32.5 points).

The >=80% verified precision target and >=80% recall target were **not met**. The >=5 percentage-point improvement over the locked baseline at no lower recall **was met**. A single run per configuration cannot establish statistical significance or reproducibility.

## Independent human evidence check

Thirty full-system verified findings were sampled across the five labeled protocols (six per protocol). The completed human sheet records **1 yes (3.3%), 5 partly (16.7%), 24 no (80.0%)**. These counts evaluate whether the **quoted passage on the cited page supports the claimed issue**, not whether the underlying study protocol is clinically sound.

The check identified recurring problems: superficially relevant but non-probative quotes, misleading snippets or table-of-contents excerpts, improper guideline assignment, and overgeneralisation from a narrow quote. Physical PDF page numbering was checked separately from printed document pagination, and differing pagination must not be counted as an error when the PDF page is correct. For observational and retrospective studies, RCT-specific SPIRIT expectations require an applicability check.

**Critical interpretation:** the human-check result is much less favourable than the label-matching verified precision. These measures sample and classify different things; they cannot be pooled or substituted for each other. The earlier project summary called label-matching precision a possible lower bound owing to incomplete labels, but the direct evidence check shows that many sampled citations themselves are inadequate. Therefore do **not** assert that the true clinical precision is higher without adjudication and a clearly defined sampling frame.

## Limitations and responsible deployment

1. Five labeled protocols, 46 labels, and only one non-expert annotator; no independent clinician adjudication or inter-rater reliability estimate.
2. The labels intentionally cover objective text-level findings, not the whole set of scientifically or clinically defensible concerns.
3. Public PDFs omit material that may exist in the real submission package (insurance, consent materials, signature pages). Absence in the public PDF is not proof of absence in a hospital submission.
4. Generic-category and page-window matching has known false-match and false-miss risks; the rule amendment was documented before the run. The 16 domain corrections were documented and re-scored without new LLM calls.
5. One model run per ablation configuration; generation is stochastic, and rows 1 and 2 use separate model generations.
6. The full system uses 30 LLM calls and 1,280,437 input tokens across five cases, compared with five calls and 207,419 input tokens for the locked baseline. Runtime increased from 568 to 2,372 seconds (approximately 4.2x).
7. The 30-finding check assessed quotations and applicability, not full end-to-end clinical decisions; many predictions need expert review.
8. Results are from the snapshot's pre-update knowledge bases. After integrating the revised KB files, report their version separately and rerun relevant tests before attributing any metrics to that version.

## Practical conclusion

The four-agent design improved coverage of manually labeled findings, but increased costs substantially and did not achieve acceptable verified precision. The independent quote-level check reveals a serious grounding problem. The project demonstrates a traceable research prototype with a defined human-review boundary, **not an autonomous ethics-review decision maker**. Priorities are evidence-verification reliability, applicability filtering by study type, independent adjudication, and repeated runs on a larger locked evaluation set.

**Source of machine results:** `eval/results/ablation-20261029-205913.json`, re-scored in `eval/results/rescore-20261029-205913-20261101-112300.json`, and `reports/results.md` in the supplied repository snapshot. The human-check results (1 yes, 5 partly, 24 no) come from Ron's completed handoff and are **not yet integrated in the repository ZIP**. Updated knowledge bases were supplied separately and are also **not included in this repository ZIP**.

---

## Addendum (Amir, 4 November 2026): the code-only rows after the sub-item guideline-code fix

While running the test suite against kb-v2, a bug in `verify_evidence` surfaced: sub-item codes such as `SPIRIT-27b`
were read as `SPIRIT-27` (unknown) and the code-only rows demoted correctly cited findings to *unverified* (18 of 21 in
row 2, 24 of 33 in row 3). The rows were re-scored from the saved evidence checks against the kb-v1 code set, with no
new model call (`eval/rescore.py --kb-codes eval/results/kb-v1-codes.json`; `reports/results.md`,
`eval/results/rescore-20261029-205913-20261104-113925.json`). The tables above show the 30 October values; corrected:

| Configuration | Verified precision (all) | Verified precision (scientific) | Unverified (all) | Recall |
|---|---:|---:|---:|---|
| Single agent + code verification (row 2) | 21/120 (17.5%) | 17/68 (25.0%) | 3 | unchanged |
| Full system without the critic (row 3) | 30/150 (20.0%) | 26/79 (32.9%) | 9 | unchanged |
| Full system (row 4) | 43/184 (23.4%) | 38/112 (33.9%) | 51 | unchanged |

Reading: the locked comparison (row 2 vs row 4) still meets the +5 pp criterion (+5.9 pp all-domain, +8.9 pp scientific,
recall +28.2 / +32.5). Row 3 vs row 4 no longer shows a precision gain from the critic (32.9% vs 33.9%); the critic's
measured contribution is recall (revision round) and routing to a human. Everything else in this document stands.
