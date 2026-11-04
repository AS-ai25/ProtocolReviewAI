# Evaluation results - ablation (Checkpoint 2)

Generated 2026-10-29 20:59 by `eval/ablation.py`, model `claude-opus-5-5`.
Test set: 5 labeled case(s) - `nct01977547` (9 labels), `nct04084990` (9 labels), `nct05199324` (9 labels), `nct05698277` (10 labels), `nct06846736` (9 labels).
All rows run with the evaluation gate bypass (`force_scientific`): the scientific stage runs even when the administrative gate fails; the decision stays RETURNED_ADMIN in that case.

Re-scored 2026-11-04 11:39 by `eval/rescore.py` from the saved findings of run `20261029-205913` (no new LLM calls): 2026-11-04: sub-item guideline codes (SPIRIT-27b) were read as unknown by verify_evidence until the regex fix of 4 November; the code-only rows 2 and 3 are re-scored from the saved evidence checks against the kb-v1 code set; rows 1 and 4 unchanged; the 16-label domain correction of 30 October stays. Sub-item guideline-code correction applied to the code-only rows from the saved evidence checks (codes of `kb-v1-codes.json`): single_verified: 18 findings verified instead of unverified, agents_no_critic: 24 findings verified instead of unverified.

## Ablation table

| # | Configuration | Precision of VERIFIED findings | Recall (coverage) of labeled findings | Unverified | LLM calls | Tokens in / out | Runtime |
|---|---|---|---|---|---|---|---|
| 1 | Single agent, no code verification | 19% (23/119) | 54% (25/46) | 0 | 5 | 207,419 / 62,590 | 548 s |
| 2 | Single agent + code verification | 18% (21/120) | 46% (21/46) | 3 | 5 | 207,419 / 66,291 | 568 s |
| 3 | Full system without the critic | 20% (30/150) | 54% (25/46) | 9 | 15 | 452,979 / 104,016 | 918 s |
| 4 | Full system (4 agents, critic, 1 revision round) | 23% (43/184) | 74% (34/46) | 51 | 30 | 1,280,437 / 271,554 | 2372 s |

Primary metric (charter v1.4, locked): precision of verified findings against blind human labels on the real-protocol test set, with recall of labeled findings as the companion metric. Unverified findings are routed to a human and counted separately, not as claims.

Matching rule: a predicted finding matches a labeled one when the domain matches and (the categories are the same or aliases in `eval/category_aliases.json`, OR the guideline reference is the same and the page is within +-1). Rejected and withdrawn findings are not predictions.

## Per case

| Configuration | Case | Decision (expected) | Verified | Matched verified | Unverified | Coverage | Missed labels | Unlabeled reported | Calls | Tokens in / out | s |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Single agent, no code verification | nct01977547 | RETURNED_ADMIN (RETURNED_ADMIN) | 23 | 4 | 0 | 4/9 | OTHER, INTERNAL_CONTRADICTION, METHOD_UNSPECIFIED, OTHER, OTHER | CONSENT_GAP, ETHICS_GAP, FORMAT_ISSUE, INTERNAL_CONTRADICTION, MISSING_CONSENT_FORM, MISSING_INSURANCE, MISSING_SECTION, MISSING_SIGNATURE_PAGE, MISSING_SPONSOR, CONSENT_GAP, ETHICS_GAP, INCONSISTENT_SAMPLE_SIZE, METHOD_UNSPECIFIED, MISSING_SECTION, NO_SAMPLE_SIZE_JUSTIFICATION, REGISTRY_MISMATCH, SAFETY_GAP | 1 | 62,762 / 13,635 | 123.3 |
| Single agent, no code verification | nct04084990 | RETURNED_ADMIN (RETURNED_ADMIN) | 24 | 6 | 0 | 6/9 | MISSING_REGISTRY_ID, MISSING_VERSION, OTHER | CONSENT_GAP, ETHICS_GAP, FORMAT_ISSUE, MISSING_DOCUMENT, MISSING_INSURANCE, MISSING_SECTION, MISSING_SIGNATURE_PAGE, MISSING_SPONSOR, CONSENT_GAP, ETHICS_GAP, INTERNAL_CONTRADICTION, NO_SAMPLE_SIZE_JUSTIFICATION, REGISTRY_MISMATCH, SAFETY_GAP | 1 | 30,366 / 13,489 | 116.2 |
| Single agent, no code verification | nct05199324 | RETURNED_ADMIN (RETURNED_ADMIN) | 18 | 3 | 0 | 4/9 | OTHER, OTHER, OTHER, OTHER, OTHER | ETHICS_GAP, INTERNAL_CONTRADICTION, MISSING_DATE, MISSING_DOCUMENT, MISSING_INSURANCE, MISSING_SPONSOR, MULTIPLE_REGISTRY_IDS, INCONSISTENT_SAMPLE_SIZE, INTERNAL_CONTRADICTION, METHOD_UNSPECIFIED, RANDOMIZATION_METHOD_UNSPECIFIED, REGISTRY_MISMATCH, SAFETY_GAP, UNJUSTIFIED_SAMPLE_SIZE | 1 | 52,141 / 11,918 | 101.8 |
| Single agent, no code verification | nct05698277 | RETURNED_ADMIN (RETURNED_ADMIN) | 25 | 6 | 0 | 4/10 | MISSING_REGISTRY_ID, OTHER, OTHER, OTHER, OTHER, OTHER | CONSENT_GAP, MISSING_CONSENT_FORM, MISSING_DOCUMENT, MISSING_ETHICS_STATEMENT, MISSING_INSURANCE, MISSING_SECTION, MISSING_SIGNATURE_PAGE, MISSING_SPONSOR, CONSENT_GAP, ETHICS_GAP, INCONSISTENT_PHASE, INCONSISTENT_SAMPLE_SIZE, METHOD_UNSPECIFIED, MISSING_SECTION, NO_DATA_MONITORING, NO_SAMPLE_SIZE_JUSTIFICATION, NO_STOPPING_RULES, REGISTRY_MISMATCH, SAFETY_GAP | 1 | 40,001 / 12,546 | 109.5 |
| Single agent, no code verification | nct06846736 | RETURNED_ADMIN (RETURNED_ADMIN) | 29 | 4 | 0 | 7/9 | MISSING_REGISTRY_ID, INTERNAL_CONTRADICTION | FORMAT_ISSUE, MISSING_CONSENT_FORM, MISSING_DATE, MISSING_INSURANCE, MISSING_PI, MISSING_SECTION, MULTIPLE_REGISTRY_IDS, OTHER, REGISTRY_MISMATCH, CONSENT_GAP, ETHICS_GAP, METHOD_UNSPECIFIED, MISSING_SECTION, NO_DATA_MONITORING, NO_HARMS_PLAN, NO_PRIMARY_OUTCOME, NO_STOPPING_RULES, REGISTRY_MISMATCH, UNJUSTIFIED_SAMPLE_SIZE | 1 | 22,149 / 11,002 | 97.1 |
| Single agent + code verification | nct01977547 | RETURNED_ADMIN (RETURNED_ADMIN) | 22 | 4 | 1 | 4/9 | OTHER, OTHER, OTHER, OTHER, OTHER | CONSENT_GAP, ETHICS_GAP, FORMAT_ISSUE, INTERNAL_CONTRADICTION, MISSING_CONSENT_FORM, MISSING_DOCUMENT, MISSING_INSURANCE, MISSING_SECTION, MISSING_SIGNATURE_PAGE, MISSING_SPONSOR, CONSENT_GAP, ETHICS_GAP, INCONSISTENT_SAMPLE_SIZE, METHOD_UNSPECIFIED, NO_SAMPLE_SIZE_JUSTIFICATION, REGISTRY_MISMATCH, SAFETY_GAP | 1 | 62,762 / 13,748 | 118.8 |
| Single agent + code verification | nct04084990 | RETURNED_ADMIN (RETURNED_ADMIN) | 25 | 5 | 1 | 6/9 | MISSING_REGISTRY_ID, MISSING_VERSION, OTHER | CONSENT_GAP, ETHICS_GAP, FORMAT_ISSUE, MISSING_DOCUMENT, MISSING_INSURANCE, MISSING_SECTION, MISSING_SIGNATURE_PAGE, MISSING_SPONSOR, CONSENT_GAP, ETHICS_GAP, INTERNAL_CONTRADICTION, METHOD_UNSPECIFIED, NO_SAMPLE_SIZE_JUSTIFICATION, REGISTRY_MISMATCH, SAFETY_GAP, UNJUSTIFIED_SAMPLE_SIZE | 1 | 30,366 / 14,804 | 124.0 |
| Single agent + code verification | nct05199324 | RETURNED_ADMIN (RETURNED_ADMIN) | 19 | 2 | 0 | 3/9 | INTERNAL_CONTRADICTION, OTHER, OTHER, OTHER, OTHER, OTHER | CONSENT_GAP, ETHICS_GAP, FORMAT_ISSUE, MISSING_DATE, MISSING_DOCUMENT, MISSING_INSURANCE, MISSING_SPONSOR, MULTIPLE_REGISTRY_IDS, CONSENT_GAP, INCONSISTENT_SAMPLE_SIZE, INTERNAL_CONTRADICTION, METHOD_UNSPECIFIED, RANDOMIZATION_METHOD_UNSPECIFIED, SAFETY_GAP, UNJUSTIFIED_SAMPLE_SIZE | 1 | 52,141 / 11,506 | 97.8 |
| Single agent + code verification | nct05698277 | RETURNED_ADMIN (RETURNED_ADMIN) | 26 | 6 | 1 | 4/10 | MISSING_REGISTRY_ID, OTHER, OTHER, OTHER, OTHER, OTHER | CONSENT_GAP, FORMAT_ISSUE, MISSING_CONSENT_FORM, MISSING_ETHICS_STATEMENT, MISSING_INSURANCE, MISSING_SECTION, MISSING_SIGNATURE_PAGE, MISSING_SPONSOR, ETHICS_GAP, INCONSISTENT_PHASE, INCONSISTENT_SAMPLE_SIZE, METHOD_UNSPECIFIED, NO_DATA_MONITORING, NO_SAMPLE_SIZE_JUSTIFICATION, NO_STOPPING_RULES, REGISTRY_MISMATCH, SAFETY_GAP, UNJUSTIFIED_SAMPLE_SIZE | 1 | 40,001 / 13,929 | 119.1 |
| Single agent + code verification | nct06846736 | RETURNED_ADMIN (RETURNED_ADMIN) | 28 | 4 | 0 | 4/9 | MISSING_REGISTRY_ID, OTHER, OTHER, OTHER, OTHER | ETHICS_GAP, FORMAT_ISSUE, MISSING_CONSENT_FORM, MISSING_DATE, MISSING_INSURANCE, MISSING_PI, MISSING_SECTION, MULTIPLE_REGISTRY_IDS, REGISTRY_MISMATCH, CONSENT_GAP, METHOD_UNSPECIFIED, NO_DATA_MONITORING, NO_HARMS_PLAN, NO_PRIMARY_OUTCOME, NO_STOPPING_RULES, REGISTRY_MISMATCH, UNJUSTIFIED_SAMPLE_SIZE | 1 | 22,149 / 12,304 | 108.2 |
| Full system without the critic | nct01977547 | RETURNED_ADMIN (RETURNED_ADMIN) | 30 | 8 | 1 | 7/9 | OTHER, OTHER | CONSENT_GAP, ETHICS_GAP, FORMAT_ISSUE, INTERNAL_CONTRADICTION, MISSING_CONSENT_FORM, MISSING_DOCUMENT, MISSING_INSURANCE, MISSING_SECTION, MISSING_SIGNATURE_PAGE, MISSING_SPONSOR, CONSENT_GAP, ETHICS_GAP, FORMAT_ISSUE, INCONSISTENT_SAMPLE_SIZE, INTERNAL_CONTRADICTION, MISSING_SECTION, NO_SAMPLE_SIZE_JUSTIFICATION, REGISTRY_MISMATCH, SAFETY_GAP | 3 | 137,811 / 24,869 | 224.3 |
| Full system without the critic | nct04084990 | RETURNED_ADMIN (RETURNED_ADMIN) | 32 | 7 | 1 | 6/9 | MISSING_REGISTRY_ID, MISSING_VERSION, OTHER | CONSENT_GAP, ETHICS_GAP, FORMAT_ISSUE, INTERNAL_CONTRADICTION, MISSING_DOCUMENT, MISSING_INSURANCE, MISSING_SIGNATURE_PAGE, MISSING_SPONSOR, REGISTRY_MISMATCH, CONSENT_GAP, ETHICS_GAP, INTERNAL_CONTRADICTION, METHOD_UNSPECIFIED, MISSING_SECTION, NO_SAMPLE_SIZE_JUSTIFICATION, REGISTRY_MISMATCH, SAFETY_GAP, UNJUSTIFIED_SAMPLE_SIZE | 3 | 70,102 / 21,905 | 190.8 |
| Full system without the critic | nct05199324 | RETURNED_ADMIN (RETURNED_ADMIN) | 24 | 2 | 3 | 2/9 | OTHER, OTHER, OTHER, OTHER, OTHER, OTHER, OTHER | CONSENT_GAP, ETHICS_GAP, FORMAT_ISSUE, INTERNAL_CONTRADICTION, MISSING_DATE, MISSING_DOCUMENT, MISSING_INSURANCE, MISSING_SPONSOR, MULTIPLE_REGISTRY_IDS, CONSENT_GAP, ETHICS_GAP, INCONSISTENT_SAMPLE_SIZE, INTERNAL_CONTRADICTION, METHOD_UNSPECIFIED, MISSING_SECTION, OTHER, RANDOMIZATION_METHOD_UNSPECIFIED, REGISTRY_MISMATCH, SAFETY_GAP, UNJUSTIFIED_SAMPLE_SIZE | 3 | 112,474 / 20,812 | 180.5 |
| Full system without the critic | nct05698277 | RETURNED_ADMIN (RETURNED_ADMIN) | 31 | 7 | 1 | 4/10 | MISSING_REGISTRY_ID, OTHER, OTHER, OTHER, OTHER, OTHER | CONSENT_GAP, FORMAT_ISSUE, INTERNAL_CONTRADICTION, MISSING_CONSENT_FORM, MISSING_DOCUMENT, MISSING_ETHICS_STATEMENT, MISSING_INSURANCE, MISSING_SECTION, MISSING_SIGNATURE_PAGE, MISSING_SPONSOR, REGISTRY_MISMATCH, CONSENT_GAP, ETHICS_GAP, INCONSISTENT_PHASE, INCONSISTENT_SAMPLE_SIZE, METHOD_UNSPECIFIED, MISSING_SECTION, NO_DATA_MONITORING, NO_SAMPLE_SIZE_JUSTIFICATION, NO_STOPPING_RULES, OTHER, SAFETY_GAP | 3 | 84,758 / 19,551 | 170.2 |
| Full system without the critic | nct06846736 | RETURNED_ADMIN (RETURNED_ADMIN) | 33 | 6 | 3 | 6/9 | MISSING_REGISTRY_ID, OTHER, OTHER | CONSENT_GAP, ETHICS_GAP, FORMAT_ISSUE, INTERNAL_CONTRADICTION, MISSING_CONSENT_FORM, MISSING_DATE, MISSING_INSURANCE, MISSING_PI, MISSING_SECTION, MULTIPLE_REGISTRY_IDS, OTHER, REGISTRY_MISMATCH, CONSENT_GAP, ETHICS_GAP, METHOD_UNSPECIFIED, NO_DATA_MONITORING, NO_HARMS_PLAN, NO_PRIMARY_OUTCOME, NO_STOPPING_RULES, REGISTRY_MISMATCH, UNJUSTIFIED_SAMPLE_SIZE | 3 | 47,834 / 16,879 | 152.2 |
| Full system (4 agents, critic, 1 revision round) | nct01977547 | RETURNED_ADMIN (RETURNED_ADMIN) | 37 | 11 | 10 | 8/9 | OTHER | CONSENT_GAP, ETHICS_GAP, FORMAT_ISSUE, INTERNAL_CONTRADICTION, MISSING_CONSENT_FORM, MISSING_DOCUMENT, MISSING_INSURANCE, MISSING_SECTION, MISSING_SIGNATURE_PAGE, MISSING_SPONSOR, REGISTRY_MISMATCH, CONSENT_GAP, ETHICS_GAP, INCONSISTENT_SAMPLE_SIZE, METHOD_UNSPECIFIED, MISSING_SECTION, NO_SAMPLE_SIZE_JUSTIFICATION, OTHER, REGISTRY_MISMATCH, SAFETY_GAP, UNJUSTIFIED_SAMPLE_SIZE | 6 | 364,797 / 61,968 | 545.1 |
| Full system (4 agents, critic, 1 revision round) | nct04084990 | RETURNED_ADMIN (RETURNED_ADMIN) | 37 | 9 | 12 | 7/9 | MISSING_REGISTRY_ID, MISSING_VERSION | CONSENT_GAP, ETHICS_GAP, FORMAT_ISSUE, INTERNAL_CONTRADICTION, MISSING_DOCUMENT, MISSING_INSURANCE, MISSING_SECTION, MISSING_SIGNATURE_PAGE, MISSING_SPONSOR, REGISTRY_MISMATCH, CONSENT_GAP, ETHICS_GAP, INTERNAL_CONTRADICTION, METHOD_UNSPECIFIED, MISSING_SECTION, NO_SAMPLE_SIZE_JUSTIFICATION, OTHER, REGISTRY_MISMATCH, SAFETY_GAP, UNJUSTIFIED_SAMPLE_SIZE | 6 | 195,068 / 51,565 | 445.4 |
| Full system (4 agents, critic, 1 revision round) | nct05199324 | RETURNED_ADMIN (RETURNED_ADMIN) | 36 | 7 | 11 | 7/9 | OTHER, OTHER | CONSENT_GAP, ETHICS_GAP, FORMAT_ISSUE, INTERNAL_CONTRADICTION, MISSING_DATE, MISSING_DOCUMENT, MISSING_INSURANCE, MISSING_SPONSOR, MULTIPLE_REGISTRY_IDS, CONSENT_GAP, ETHICS_GAP, FORMAT_ISSUE, INCONSISTENT_SAMPLE_SIZE, INTERNAL_CONTRADICTION, METHOD_UNSPECIFIED, MISSING_SECTION, OTHER, RANDOMIZATION_METHOD_UNSPECIFIED, SAFETY_GAP, UNJUSTIFIED_SAMPLE_SIZE | 6 | 361,588 / 67,611 | 578.1 |
| Full system (4 agents, critic, 1 revision round) | nct05698277 | RETURNED_ADMIN (RETURNED_ADMIN) | 32 | 10 | 10 | 6/10 | MISSING_REGISTRY_ID, OTHER, OTHER, OTHER | CONSENT_GAP, FORMAT_ISSUE, INTERNAL_CONTRADICTION, MISSING_CONSENT_FORM, MISSING_DOCUMENT, MISSING_ETHICS_STATEMENT, MISSING_INSURANCE, MISSING_SECTION, MISSING_SIGNATURE_PAGE, MISSING_SPONSOR, REGISTRY_MISMATCH, CONSENT_GAP, ETHICS_GAP, INCONSISTENT_PHASE, INCONSISTENT_SAMPLE_SIZE, INTERNAL_CONTRADICTION, METHOD_UNSPECIFIED, MISSING_SECTION, NO_DATA_MONITORING, NO_SAMPLE_SIZE_JUSTIFICATION, NO_STOPPING_RULES, OTHER, SAFETY_GAP | 6 | 225,089 / 46,611 | 414.0 |
| Full system (4 agents, critic, 1 revision round) | nct06846736 | RETURNED_ADMIN (RETURNED_ADMIN) | 42 | 6 | 8 | 6/9 | MISSING_REGISTRY_ID, OTHER, OTHER | CONSENT_GAP, ETHICS_GAP, FORMAT_ISSUE, INTERNAL_CONTRADICTION, MISSING_CONSENT_FORM, MISSING_DATE, MISSING_INSURANCE, MISSING_PI, MISSING_SECTION, MULTIPLE_REGISTRY_IDS, OTHER, REGISTRY_MISMATCH, CONSENT_GAP, ETHICS_GAP, FORMAT_ISSUE, METHOD_UNSPECIFIED, MISSING_SECTION, NO_DATA_MONITORING, NO_HARMS_PLAN, NO_PRIMARY_OUTCOME, NO_STOPPING_RULES, OTHER, REGISTRY_MISMATCH, UNJUSTIFIED_SAMPLE_SIZE | 6 | 133,895 / 43,799 | 389.3 |

## Reading the rows

1. **Single agent, no code verification** - one LLM call; the model's own status stands (unmarked findings count as verified). Measures how many of the model's claims a human would have to re-check.
2. **Single agent + code verification** - the same call; a quote the code cannot locate in the PDF or an unknown guideline code makes the finding unverified. This is the Single-Agent Baseline of the charter.
3. **Full system without the critic** - administrative agent + scientific reviewer, code-only verification of the reviewer's findings, no revision round. Isolates the contribution of the agent split.
4. **Full system** - row 3 plus the Scientific Critic (verdict per finding, missed issues, at most one revision round). The difference between rows 3 and 4 is the critic's contribution.
## Scientific domain only (reduced-scope view)

Labels and predictions restricted to the scientific domain. The five labeled protocols are public registry documents without submission appendices; the labeler recorded what is wrong *in the protocol text*, not which package documents are absent, so this view compares like with like.

| # | Configuration | Precision of VERIFIED findings | Recall (coverage) of labeled findings | Unverified |
|---|---|---|---|---|
| 1 | Single agent, no code verification | 29% (19/66) | 57% (21/37) | 0 |
| 2 | Single agent + code verification | 25% (17/68) | 46% (17/37) | 0 |
| 3 | Full system without the critic | 33% (26/79) | 57% (21/37) | 9 |
| 4 | Full system (4 agents, critic, 1 revision round) | 34% (38/112) | 78% (29/37) | 50 |

| Configuration | Case | Verified | Matched verified | Unverified | Coverage | Missed labels |
|---|---|---|---|---|---|---|
| Single agent, no code verification | nct01977547 | 12 | 4 | 0 | 4/8 | INTERNAL_CONTRADICTION, METHOD_UNSPECIFIED, OTHER, OTHER |
| Single agent, no code verification | nct04084990 | 15 | 6 | 0 | 6/7 | OTHER |
| Single agent, no code verification | nct05199324 | 10 | 3 | 0 | 4/9 | OTHER, OTHER, OTHER, OTHER, OTHER |
| Single agent, no code verification | nct05698277 | 16 | 5 | 0 | 3/8 | OTHER, OTHER, OTHER, OTHER, OTHER |
| Single agent, no code verification | nct06846736 | 13 | 1 | 0 | 4/5 | INTERNAL_CONTRADICTION |
| Single agent + code verification | nct01977547 | 11 | 4 | 0 | 4/8 | OTHER, OTHER, OTHER, OTHER |
| Single agent + code verification | nct04084990 | 17 | 5 | 0 | 6/7 | OTHER |
| Single agent + code verification | nct05199324 | 10 | 2 | 0 | 3/9 | INTERNAL_CONTRADICTION, OTHER, OTHER, OTHER, OTHER, OTHER |
| Single agent + code verification | nct05698277 | 17 | 5 | 0 | 3/8 | OTHER, OTHER, OTHER, OTHER, OTHER |
| Single agent + code verification | nct06846736 | 13 | 1 | 0 | 1/5 | OTHER, OTHER, OTHER, OTHER |
| Full system without the critic | nct01977547 | 16 | 8 | 1 | 7/8 | OTHER |
| Full system without the critic | nct04084990 | 19 | 7 | 1 | 6/7 | OTHER |
| Full system without the critic | nct05199324 | 13 | 2 | 3 | 2/9 | OTHER, OTHER, OTHER, OTHER, OTHER, OTHER, OTHER |
| Full system without the critic | nct05698277 | 18 | 6 | 1 | 3/8 | OTHER, OTHER, OTHER, OTHER, OTHER |
| Full system without the critic | nct06846736 | 13 | 3 | 3 | 3/5 | OTHER, OTHER |
| Full system (4 agents, critic, 1 revision round) | nct01977547 | 20 | 10 | 10 | 7/8 | OTHER |
| Full system (4 agents, critic, 1 revision round) | nct04084990 | 25 | 9 | 11 | 7/7 | - |
| Full system (4 agents, critic, 1 revision round) | nct05199324 | 24 | 7 | 11 | 7/9 | OTHER, OTHER |
| Full system (4 agents, critic, 1 revision round) | nct05698277 | 20 | 9 | 10 | 5/8 | OTHER, OTHER, OTHER |
| Full system (4 agents, critic, 1 revision round) | nct06846736 | 23 | 3 | 8 | 3/5 | OTHER, OTHER |


## Critic contribution (full system, scientific findings)

What the Scientific Critic did with the reviewer's findings, per protocol. `matched` = the finding matches a blind label. A critic that works should leave a higher matched share among the findings it verified than among those it sent to a human (unverified) or rejected.

| Case | Reviewer findings (no-critic run) | Full run: verified (matched) | unverified (matched) | rejected / withdrawn (matched) | critic-raised issues |
|---|---|---|---|---|---|
| nct01977547 | 17 | 20 (10) | 4 (1) | 1 (0) | 6 |
| nct04084990 | 20 | 25 (9) | 2 (1) | 0 (0) | 9 |
| nct05199324 | 16 | 24 (7) | 3 (0) | 1 (0) | 8 |
| nct05698277 | 19 | 20 (9) | 4 (1) | 1 (0) | 6 |
| nct06846736 | 16 | 23 (3) | 1 (0) | 0 (0) | 7 |
| **all** | 88 | 112 (38) | 14 (3) | 3 (0) | 36 |

Matched share: verified 38/112 = 34%, unverified 3/14 = 21%, rejected / withdrawn 0/3 = 0%. Critic-raised issues (SCI-C...) carry no evidence and are always routed to a human; they are never scored as claims.


## Administrative findings outside the label scope

Verified administrative findings of the full system across the five protocols, by category. Package-completeness items (consent form, insurance, signature page, sponsor statement, referenced documents) are true for every public registry protocol and were deliberately not labeled; they dominate the administrative false positives of the charter table.

| Category | Verified findings |
|---|---|
| FORMAT_ISSUE | 11 |
| INTERNAL_CONTRADICTION | 10 |
| MISSING_SECTION | 7 |
| MISSING_DOCUMENT | 6 |
| MISSING_INSURANCE | 5 |
| CONSENT_GAP | 5 |
| MISSING_SPONSOR | 4 |
| MISSING_SIGNATURE_PAGE | 4 |
| ETHICS_GAP | 4 |
| MISSING_CONSENT_FORM | 3 |
| REGISTRY_MISMATCH | 3 |
| OTHER | 2 |
| MISSING_DATE | 2 |
| MULTIPLE_REGISTRY_IDS | 2 |
| MISSING_ETHICS_STATEMENT | 1 |
| MISSING_VERSION | 1 |
| MISSING_PI | 1 |
| MISSING_CONTACT | 1 |
