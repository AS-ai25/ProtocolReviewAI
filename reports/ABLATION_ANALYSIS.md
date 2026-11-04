# Ablation analysis and interpretation

**Dataset:** five blind-labeled real protocols, 46 all-domain and 37 scientific labels. **Run:** 2026-10-29; **re-score file:** 2026-11-01. No new model calls during re-score.

## Four controlled configurations

| Configuration | Verified precision | Label recall | Unverified | LLM calls | Input tokens | Runtime (s) |
|---|---:|---:|---:|---:|---:|---:|
| Single agent, no code verification | 23/119 (19.3%) | 25/46 (54.3%) | 0 | 5 | 207,419 | 547.9 |
| Single agent + code verification | 13/102 (12.7%) | 21/46 (45.7%) | 21 | 5 | 207,419 | 567.9 |
| Full system without the critic | 19/126 (15.1%) | 25/46 (54.3%) | 33 | 15 | 452,979 | 918.0 |
| Full system (4 agents, critic, 1 revision round) | 43/184 (23.4%) | 34/46 (73.9%) | 51 | 30 | 1,280,437 | 2,371.9 |

## Scientific-only scores

| Configuration | Verified precision | Label recall | Unverified | LLM calls | Input tokens | Runtime (s) |
|---|---:|---:|---:|---:|---:|---:|
| Single agent, no code verification | 19/66 (28.8%) | 21/37 (56.8%) | 0 | 5 | 207,419 | 547.9 |
| Single agent + code verification | 9/50 (18.0%) | 17/37 (45.9%) | 18 | 5 | 207,419 | 567.9 |
| Full system without the critic | 15/57 (26.3%) | 21/37 (56.8%) | 31 | 15 | 452,979 | 918.0 |
| Full system (4 agents, critic, 1 revision round) | 38/112 (33.9%) | 29/37 (78.4%) | 50 | 30 | 1,280,437 | 2,371.9 |

## What comparisons do and do not isolate

1. **Row 1 vs 2:** code verification demotes some claims to unverified, but the rows are separate stochastic LLM runs. Consequently the observed metric difference is *not* a clean causal estimate of the verifier's benefit.
2. **Row 2 vs 3:** role splitting plus a different pipeline improves recall from 45.7% to 54.3% (all domains), but precision rises only 12.7% to 15.1%. This comparison bundles more than one implementation difference.
3. **Row 3 vs 4:** addition of the critic and a revision round increases recall from 54.3% to 73.9% and precision from 15.1% to 23.4% in the all-domain view. It **does not isolate the critic alone**, because the revision round is also added.
4. **Rows 2 vs 4 (locked comparison):** +10.7 pp verified precision and +28.2 pp label recall, for about 6.2x input tokens and 4.2x runtime. This meets the relative improvement criterion, but not the absolute quality targets.

## Resource trade-offs

- Baseline (row 2): 5 calls; 207,419 input tokens; 66,291 output tokens; 567.9 s across five cases.
- Full (row 4): 30 calls; 1,280,437 input tokens; 271,554 output tokens; 2,371.9 s across five cases.
- Unverified handoffs: 21 vs 51 across the five cases. These are **not** verified claims.
- The full system generated 184 verified predictions, of which only 43 matched blinded all-domain labels under the project's conservative rule. This is **not** proof that the remaining 141 are all false; their evidence quality must be assessed independently.

## Human-check cross-check

The final 30-finding audit reports 1 yes / 5 partly / 24 no. The review used the page and quote plus surrounding protocol context, and did not treat a correct quote location as sufficient proof of a problem. Because this directly challenges evidence grounding, it weakens any broad claim that a finding is trustworthy merely because code verification or a critic marked it `verified`.

## Presentation-safe conclusion

**Observed benefit:** increased labeled-finding recall at a measurable resource cost. **Not demonstrated:** deployment-ready clinical accuracy, an isolated causal benefit of the critic independent of revision, or statistically robust generalisation. Recommend a supervised pre-review workflow and independent clinical adjudication before real-world use.

## Recommended next experiments (not yet completed)

- Repeat identical configurations across multiple random seeds with confidence intervals.
- Hold reviewer outputs fixed when comparing code verification on/off.
- Isolate critic verdicting from revision round in separate configurations.
- Add study-type-aware guideline applicability and stronger quote-to-claim support checks.
- Obtain a second independent labeler and adjudicate disagreements; expand the blinded labeled set before tuning.

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
