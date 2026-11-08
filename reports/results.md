# Evaluation results - ablation (Checkpoint 2)

Generated 2026-10-29 20:59 by `eval/ablation.py`, model `claude-opus-5-5`.
Test set: 5 labeled case(s) - `nct01977547` (9 labels), `nct04084990` (9 labels), `nct05199324` (9 labels), `nct05698277` (10 labels), `nct06846736` (9 labels).
All rows run with the evaluation gate bypass (`force_scientific`): the scientific stage runs even when the administrative gate fails; the decision stays RETURNED_ADMIN in that case.

Re-scored 2026-11-08 17:21 by `eval/rescore.py` from the saved findings of run(s) `20261029-205913`, `20261108-154153` (no new LLM calls): 2026-11-04: sub-item guideline codes (SPIRIT-27b) were read as unknown by verify_evidence until the regex fix of 4 November; rows 2 and 3 re-scored from the saved evidence checks against the kb-v1 code set; rows 1 and 4 unchanged; the 16-label domain correction of 30 October stays. 2026-11-08: row labels renamed 'Single LLM call'; row 0 (rules only) and the protocol-level bootstrap added (mentor M2, M9); rows 2', 3', 4' are the v1.7 run of 8 November (tool use + deterministic evidence tools, knowledge base kb-v2). Sub-item guideline-code correction applied to the code-only rows from the saved evidence checks (codes of `kb-v1-codes.json`): single_verified: 18 findings verified instead of unverified, agents_no_critic: 24 findings verified instead of unverified. Row 0 (rules only) is computed from the deterministic findings saved with the runs.

## Ablation table

| # | Configuration | Precision of VERIFIED findings | Recall (coverage) of labeled findings | Unverified | LLM calls | Tokens in / out | Runtime |
|---|---|---|---|---|---|---|---|
| 0 | Rules only (29 deterministic checks, no LLM) | 9% (4/44) | 9% (4/46) | 0 | 0 | 0 / 0 | 0 s |
| 1 | Single LLM call, no code verification | 19% (23/119) | 54% (25/46) | 0 | 5 | 207,419 / 62,590 | 548 s |
| 2 | Single LLM call + code verification | 18% (21/120) | 46% (21/46) | 3 | 5 | 207,419 / 66,291 | 568 s |
| 3 | Full system without the critic | 20% (30/150) | 54% (25/46) | 9 | 15 | 452,979 / 104,016 | 918 s |
| 4 | Full system (4 agents, critic, 1 revision round) | 23% (43/184) | 74% (34/46) | 51 | 30 | 1,280,437 / 271,554 | 2372 s |
| 2' | Single agent with tool use + code verification | 18% (10/57) | 46% (21/46) | 48 | 5 | 728,543 / 101,466 | 882 s |
| 3' | Full system without the critic, reviewer with tool use | 17% (12/70) | 59% (27/46) | 79 | 15 | 1,042,678 / 133,876 | 1190 s |
| 4' | Full system, reviewer and critic with tool use | 21% (17/80) | 65% (30/46) | 145 | 30 | 3,654,874 / 388,308 | 3418 s |

Primary metric (charter v1.4, locked): precision of verified findings against blind human labels on the real-protocol test set, with recall of labeled findings as the companion metric. Unverified findings are routed to a human and counted separately, not as claims.

Matching rule: a predicted finding matches a labeled one when the domain matches and (the categories are the same or aliases in `eval/category_aliases.json`, OR the guideline reference is the same and the page is within +-1). Rejected and withdrawn findings are not predictions.

## Per case

| Configuration | Case | Decision (expected) | Verified | Matched verified | Unverified | Coverage | Missed labels | Unlabeled reported | Calls | Tokens in / out | s |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Rules only (29 deterministic checks, no LLM) | nct01977547 | - (RETURNED_ADMIN) | 6 | 0 | 0 | 0/9 | OTHER, INTERNAL_CONTRADICTION, INTERNAL_CONTRADICTION, METHOD_UNSPECIFIED, METHOD_UNSPECIFIED, OTHER, OTHER, OTHER, OTHER | MISSING_CONSENT_FORM, MISSING_INSURANCE, MISSING_SIGNATURE_PAGE, MISSING_SPONSOR, INCONSISTENT_SAMPLE_SIZE, NO_SAMPLE_SIZE_JUSTIFICATION | 0 | 0 / 0 | 0.0 |
| Rules only (29 deterministic checks, no LLM) | nct04084990 | - (RETURNED_ADMIN) | 6 | 1 | 0 | 1/9 | MISSING_REGISTRY_ID, MISSING_VERSION, INTERNAL_CONTRADICTION, METHOD_UNSPECIFIED, METHOD_UNSPECIFIED, METHOD_UNSPECIFIED, OTHER, OTHER | MISSING_INSURANCE, MISSING_SIGNATURE_PAGE, MISSING_SPONSOR, NO_SAMPLE_SIZE_JUSTIFICATION, REGISTRY_MISMATCH | 0 | 0 / 0 | 0.0 |
| Rules only (29 deterministic checks, no LLM) | nct05199324 | - (RETURNED_ADMIN) | 6 | 0 | 0 | 0/9 | INTERNAL_CONTRADICTION, NO_DATA_MONITORING, OTHER, OTHER, OTHER, OTHER, OTHER, OTHER, OTHER | MISSING_DATE, MISSING_INSURANCE, MISSING_SPONSOR, MULTIPLE_REGISTRY_IDS, INCONSISTENT_SAMPLE_SIZE, RANDOMIZATION_METHOD_UNSPECIFIED | 0 | 0 / 0 | 0.0 |
| Rules only (29 deterministic checks, no LLM) | nct05698277 | - (RETURNED_ADMIN) | 10 | 0 | 0 | 0/10 | INTERNAL_CONTRADICTION, MISSING_REGISTRY_ID, INTERNAL_CONTRADICTION, INTERNAL_CONTRADICTION, METHOD_UNSPECIFIED, OTHER, OTHER, OTHER, OTHER, OTHER | MISSING_CONSENT_FORM, MISSING_ETHICS_STATEMENT, MISSING_INSURANCE, MISSING_SIGNATURE_PAGE, MISSING_SPONSOR, INCONSISTENT_PHASE, INCONSISTENT_SAMPLE_SIZE, NO_DATA_MONITORING, NO_SAMPLE_SIZE_JUSTIFICATION, NO_STOPPING_RULES | 0 | 0 / 0 | 0.0 |
| Rules only (29 deterministic checks, no LLM) | nct06846736 | - (RETURNED_ADMIN) | 16 | 3 | 0 | 3/9 | MISSING_REGISTRY_ID, INTERNAL_CONTRADICTION, OTHER, OTHER, OTHER, OTHER | MISSING_CONSENT_FORM, MISSING_DATE, MISSING_INSURANCE, MISSING_PI, MISSING_SECTION, MULTIPLE_REGISTRY_IDS, NO_DATA_MONITORING, NO_HARMS_PLAN, NO_PRIMARY_OUTCOME, NO_STOPPING_RULES | 0 | 0 / 0 | 0.0 |
| Single LLM call, no code verification | nct01977547 | RETURNED_ADMIN (RETURNED_ADMIN) | 23 | 4 | 0 | 4/9 | OTHER, INTERNAL_CONTRADICTION, METHOD_UNSPECIFIED, OTHER, OTHER | CONSENT_GAP, ETHICS_GAP, FORMAT_ISSUE, INTERNAL_CONTRADICTION, MISSING_CONSENT_FORM, MISSING_INSURANCE, MISSING_SECTION, MISSING_SIGNATURE_PAGE, MISSING_SPONSOR, CONSENT_GAP, ETHICS_GAP, INCONSISTENT_SAMPLE_SIZE, METHOD_UNSPECIFIED, MISSING_SECTION, NO_SAMPLE_SIZE_JUSTIFICATION, REGISTRY_MISMATCH, SAFETY_GAP | 1 | 62,762 / 13,635 | 123.3 |
| Single LLM call, no code verification | nct04084990 | RETURNED_ADMIN (RETURNED_ADMIN) | 24 | 6 | 0 | 6/9 | MISSING_REGISTRY_ID, MISSING_VERSION, OTHER | CONSENT_GAP, ETHICS_GAP, FORMAT_ISSUE, MISSING_DOCUMENT, MISSING_INSURANCE, MISSING_SECTION, MISSING_SIGNATURE_PAGE, MISSING_SPONSOR, CONSENT_GAP, ETHICS_GAP, INTERNAL_CONTRADICTION, NO_SAMPLE_SIZE_JUSTIFICATION, REGISTRY_MISMATCH, SAFETY_GAP | 1 | 30,366 / 13,489 | 116.2 |
| Single LLM call, no code verification | nct05199324 | RETURNED_ADMIN (RETURNED_ADMIN) | 18 | 3 | 0 | 4/9 | OTHER, OTHER, OTHER, OTHER, OTHER | ETHICS_GAP, INTERNAL_CONTRADICTION, MISSING_DATE, MISSING_DOCUMENT, MISSING_INSURANCE, MISSING_SPONSOR, MULTIPLE_REGISTRY_IDS, INCONSISTENT_SAMPLE_SIZE, INTERNAL_CONTRADICTION, METHOD_UNSPECIFIED, RANDOMIZATION_METHOD_UNSPECIFIED, REGISTRY_MISMATCH, SAFETY_GAP, UNJUSTIFIED_SAMPLE_SIZE | 1 | 52,141 / 11,918 | 101.8 |
| Single LLM call, no code verification | nct05698277 | RETURNED_ADMIN (RETURNED_ADMIN) | 25 | 6 | 0 | 4/10 | MISSING_REGISTRY_ID, OTHER, OTHER, OTHER, OTHER, OTHER | CONSENT_GAP, MISSING_CONSENT_FORM, MISSING_DOCUMENT, MISSING_ETHICS_STATEMENT, MISSING_INSURANCE, MISSING_SECTION, MISSING_SIGNATURE_PAGE, MISSING_SPONSOR, CONSENT_GAP, ETHICS_GAP, INCONSISTENT_PHASE, INCONSISTENT_SAMPLE_SIZE, METHOD_UNSPECIFIED, MISSING_SECTION, NO_DATA_MONITORING, NO_SAMPLE_SIZE_JUSTIFICATION, NO_STOPPING_RULES, REGISTRY_MISMATCH, SAFETY_GAP | 1 | 40,001 / 12,546 | 109.5 |
| Single LLM call, no code verification | nct06846736 | RETURNED_ADMIN (RETURNED_ADMIN) | 29 | 4 | 0 | 7/9 | MISSING_REGISTRY_ID, INTERNAL_CONTRADICTION | FORMAT_ISSUE, MISSING_CONSENT_FORM, MISSING_DATE, MISSING_INSURANCE, MISSING_PI, MISSING_SECTION, MULTIPLE_REGISTRY_IDS, OTHER, REGISTRY_MISMATCH, CONSENT_GAP, ETHICS_GAP, METHOD_UNSPECIFIED, MISSING_SECTION, NO_DATA_MONITORING, NO_HARMS_PLAN, NO_PRIMARY_OUTCOME, NO_STOPPING_RULES, REGISTRY_MISMATCH, UNJUSTIFIED_SAMPLE_SIZE | 1 | 22,149 / 11,002 | 97.1 |
| Single LLM call + code verification | nct01977547 | RETURNED_ADMIN (RETURNED_ADMIN) | 22 | 4 | 1 | 4/9 | OTHER, OTHER, OTHER, OTHER, OTHER | CONSENT_GAP, ETHICS_GAP, FORMAT_ISSUE, INTERNAL_CONTRADICTION, MISSING_CONSENT_FORM, MISSING_DOCUMENT, MISSING_INSURANCE, MISSING_SECTION, MISSING_SIGNATURE_PAGE, MISSING_SPONSOR, CONSENT_GAP, ETHICS_GAP, INCONSISTENT_SAMPLE_SIZE, METHOD_UNSPECIFIED, NO_SAMPLE_SIZE_JUSTIFICATION, REGISTRY_MISMATCH, SAFETY_GAP | 1 | 62,762 / 13,748 | 118.8 |
| Single LLM call + code verification | nct04084990 | RETURNED_ADMIN (RETURNED_ADMIN) | 25 | 5 | 1 | 6/9 | MISSING_REGISTRY_ID, MISSING_VERSION, OTHER | CONSENT_GAP, ETHICS_GAP, FORMAT_ISSUE, MISSING_DOCUMENT, MISSING_INSURANCE, MISSING_SECTION, MISSING_SIGNATURE_PAGE, MISSING_SPONSOR, CONSENT_GAP, ETHICS_GAP, INTERNAL_CONTRADICTION, METHOD_UNSPECIFIED, NO_SAMPLE_SIZE_JUSTIFICATION, REGISTRY_MISMATCH, SAFETY_GAP, UNJUSTIFIED_SAMPLE_SIZE | 1 | 30,366 / 14,804 | 124.0 |
| Single LLM call + code verification | nct05199324 | RETURNED_ADMIN (RETURNED_ADMIN) | 19 | 2 | 0 | 3/9 | INTERNAL_CONTRADICTION, OTHER, OTHER, OTHER, OTHER, OTHER | CONSENT_GAP, ETHICS_GAP, FORMAT_ISSUE, MISSING_DATE, MISSING_DOCUMENT, MISSING_INSURANCE, MISSING_SPONSOR, MULTIPLE_REGISTRY_IDS, CONSENT_GAP, INCONSISTENT_SAMPLE_SIZE, INTERNAL_CONTRADICTION, METHOD_UNSPECIFIED, RANDOMIZATION_METHOD_UNSPECIFIED, SAFETY_GAP, UNJUSTIFIED_SAMPLE_SIZE | 1 | 52,141 / 11,506 | 97.8 |
| Single LLM call + code verification | nct05698277 | RETURNED_ADMIN (RETURNED_ADMIN) | 26 | 6 | 1 | 4/10 | MISSING_REGISTRY_ID, OTHER, OTHER, OTHER, OTHER, OTHER | CONSENT_GAP, FORMAT_ISSUE, MISSING_CONSENT_FORM, MISSING_ETHICS_STATEMENT, MISSING_INSURANCE, MISSING_SECTION, MISSING_SIGNATURE_PAGE, MISSING_SPONSOR, ETHICS_GAP, INCONSISTENT_PHASE, INCONSISTENT_SAMPLE_SIZE, METHOD_UNSPECIFIED, NO_DATA_MONITORING, NO_SAMPLE_SIZE_JUSTIFICATION, NO_STOPPING_RULES, REGISTRY_MISMATCH, SAFETY_GAP, UNJUSTIFIED_SAMPLE_SIZE | 1 | 40,001 / 13,929 | 119.1 |
| Single LLM call + code verification | nct06846736 | RETURNED_ADMIN (RETURNED_ADMIN) | 28 | 4 | 0 | 4/9 | MISSING_REGISTRY_ID, OTHER, OTHER, OTHER, OTHER | ETHICS_GAP, FORMAT_ISSUE, MISSING_CONSENT_FORM, MISSING_DATE, MISSING_INSURANCE, MISSING_PI, MISSING_SECTION, MULTIPLE_REGISTRY_IDS, REGISTRY_MISMATCH, CONSENT_GAP, METHOD_UNSPECIFIED, NO_DATA_MONITORING, NO_HARMS_PLAN, NO_PRIMARY_OUTCOME, NO_STOPPING_RULES, REGISTRY_MISMATCH, UNJUSTIFIED_SAMPLE_SIZE | 1 | 22,149 / 12,304 | 108.2 |
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
| Single agent with tool use + code verification | nct01977547 | RETURNED_ADMIN (RETURNED_ADMIN) | 9 | 2 | 11 | 5/9 | OTHER, METHOD_UNSPECIFIED, OTHER, OTHER | ETHICS_GAP, FORMAT_ISSUE, INTERNAL_CONTRADICTION, MISSING_CONSENT_FORM, MISSING_DOCUMENT, MISSING_INSURANCE, MISSING_SECTION, MISSING_SIGNATURE_PAGE, MISSING_SPONSOR, ETHICS_GAP, INCONSISTENT_SAMPLE_SIZE, METHOD_UNSPECIFIED, NO_SAMPLE_SIZE_JUSTIFICATION, REGISTRY_MISMATCH, SAFETY_GAP | 1 | 210,963 / 20,219 | 179.1 |
| Single agent with tool use + code verification | nct04084990 | RETURNED_ADMIN (RETURNED_ADMIN) | 8 | 2 | 14 | 5/9 | MISSING_REGISTRY_ID, MISSING_VERSION, METHOD_UNSPECIFIED, METHOD_UNSPECIFIED | CONSENT_GAP, ETHICS_GAP, FORMAT_ISSUE, MISSING_DOCUMENT, MISSING_INSURANCE, MISSING_SECTION, MISSING_SIGNATURE_PAGE, MISSING_SPONSOR, CONSENT_GAP, ETHICS_GAP, INTERNAL_CONTRADICTION, MISSING_SECTION, NO_SAMPLE_SIZE_JUSTIFICATION, REGISTRY_MISMATCH, SAFETY_GAP, UNJUSTIFIED_SAMPLE_SIZE | 1 | 114,673 / 23,038 | 198.4 |
| Single agent with tool use + code verification | nct05199324 | RETURNED_ADMIN (RETURNED_ADMIN) | 9 | 1 | 9 | 4/9 | INTERNAL_CONTRADICTION, NO_DATA_MONITORING, OTHER, OTHER, OTHER | CONSENT_GAP, ETHICS_GAP, FORMAT_ISSUE, INTERNAL_CONTRADICTION, MISSING_DATE, MISSING_INSURANCE, MISSING_SPONSOR, MULTIPLE_REGISTRY_IDS, CONSENT_GAP, INCONSISTENT_SAMPLE_SIZE, METHOD_UNSPECIFIED, MISSING_SECTION, RANDOMIZATION_METHOD_UNSPECIFIED, SAFETY_GAP | 1 | 178,652 / 21,126 | 181.6 |
| Single agent with tool use + code verification | nct05698277 | RETURNED_ADMIN (RETURNED_ADMIN) | 14 | 1 | 7 | 3/10 | INTERNAL_CONTRADICTION, MISSING_REGISTRY_ID, OTHER, OTHER, OTHER, OTHER, OTHER | FORMAT_ISSUE, INTERNAL_CONTRADICTION, MISSING_CONSENT_FORM, MISSING_ETHICS_STATEMENT, MISSING_INSURANCE, MISSING_SECTION, MISSING_SIGNATURE_PAGE, MISSING_SPONSOR, CONSENT_GAP, ETHICS_GAP, INCONSISTENT_PHASE, INCONSISTENT_SAMPLE_SIZE, INTERNAL_CONTRADICTION, METHOD_UNSPECIFIED, NO_DATA_MONITORING, NO_SAMPLE_SIZE_JUSTIFICATION, NO_STOPPING_RULES, SAFETY_GAP | 1 | 140,182 / 21,181 | 185.1 |
| Single agent with tool use + code verification | nct06846736 | RETURNED_ADMIN (RETURNED_ADMIN) | 17 | 4 | 7 | 4/9 | MISSING_REGISTRY_ID, OTHER, OTHER, OTHER, OTHER | ETHICS_GAP, MISSING_CONSENT_FORM, MISSING_DATE, MISSING_INSURANCE, MISSING_PI, MISSING_SECTION, MULTIPLE_REGISTRY_IDS, REGISTRY_MISMATCH, CONSENT_GAP, METHOD_UNSPECIFIED, NO_DATA_MONITORING, NO_HARMS_PLAN, NO_PRIMARY_OUTCOME, NO_STOPPING_RULES | 1 | 84,073 / 15,902 | 138.0 |
| Full system without the critic, reviewer with tool use | nct01977547 | RETURNED_ADMIN (RETURNED_ADMIN) | 14 | 4 | 16 | 7/9 | OTHER, OTHER | ETHICS_GAP, FORMAT_ISSUE, INTERNAL_CONTRADICTION, MISSING_CONSENT_FORM, MISSING_DOCUMENT, MISSING_INSURANCE, MISSING_SECTION, MISSING_SIGNATURE_PAGE, MISSING_SPONSOR, REGISTRY_MISMATCH, CONSENT_GAP, ETHICS_GAP, FORMAT_ISSUE, INCONSISTENT_SAMPLE_SIZE, INTERNAL_CONTRADICTION, MISSING_SECTION, NO_SAMPLE_SIZE_JUSTIFICATION, REGISTRY_MISMATCH, SAFETY_GAP | 3 | 287,682 / 33,408 | 295.7 |
| Full system without the critic, reviewer with tool use | nct04084990 | RETURNED_ADMIN (RETURNED_ADMIN) | 9 | 2 | 21 | 6/9 | MISSING_REGISTRY_ID, MISSING_VERSION, METHOD_UNSPECIFIED | CONSENT_GAP, ETHICS_GAP, FORMAT_ISSUE, INTERNAL_CONTRADICTION, MISSING_DOCUMENT, MISSING_INSURANCE, MISSING_SIGNATURE_PAGE, MISSING_SPONSOR, OTHER, REGISTRY_MISMATCH, CONSENT_GAP, ETHICS_GAP, FORMAT_ISSUE, INTERNAL_CONTRADICTION, MISSING_SECTION, NO_SAMPLE_SIZE_JUSTIFICATION, REGISTRY_MISMATCH, SAFETY_GAP | 3 | 149,395 / 22,822 | 207.0 |
| Full system without the critic, reviewer with tool use | nct05199324 | RETURNED_ADMIN (RETURNED_ADMIN) | 12 | 1 | 14 | 5/9 | OTHER, OTHER, OTHER, OTHER | CONSENT_GAP, ETHICS_GAP, FORMAT_ISSUE, INTERNAL_CONTRADICTION, MISSING_DATE, MISSING_INSURANCE, MISSING_SPONSOR, MULTIPLE_REGISTRY_IDS, OTHER, CONSENT_GAP, INCONSISTENT_SAMPLE_SIZE, METHOD_UNSPECIFIED, MISSING_SECTION, OTHER, RANDOMIZATION_METHOD_UNSPECIFIED, SAFETY_GAP, UNJUSTIFIED_SAMPLE_SIZE | 3 | 236,413 / 29,289 | 254.6 |
| Full system without the critic, reviewer with tool use | nct05698277 | RETURNED_ADMIN (RETURNED_ADMIN) | 15 | 1 | 13 | 3/10 | INTERNAL_CONTRADICTION, MISSING_REGISTRY_ID, METHOD_UNSPECIFIED, OTHER, OTHER, OTHER, OTHER | CONSENT_GAP, FORMAT_ISSUE, INTERNAL_CONTRADICTION, MISSING_CONSENT_FORM, MISSING_DOCUMENT, MISSING_ETHICS_STATEMENT, MISSING_INSURANCE, MISSING_SECTION, MISSING_SIGNATURE_PAGE, MISSING_SPONSOR, REGISTRY_MISMATCH, CONSENT_GAP, INCONSISTENT_PHASE, INCONSISTENT_SAMPLE_SIZE, INTERNAL_CONTRADICTION, METHOD_UNSPECIFIED, MISSING_SECTION, NO_DATA_MONITORING, NO_SAMPLE_SIZE_JUSTIFICATION, NO_STOPPING_RULES, SAFETY_GAP, UNJUSTIFIED_SAMPLE_SIZE | 3 | 266,797 / 25,168 | 225.2 |
| Full system without the critic, reviewer with tool use | nct06846736 | RETURNED_ADMIN (RETURNED_ADMIN) | 20 | 4 | 15 | 6/9 | MISSING_REGISTRY_ID, OTHER, OTHER | CONSENT_GAP, ETHICS_GAP, FORMAT_ISSUE, INTERNAL_CONTRADICTION, METHOD_UNSPECIFIED, MISSING_CONSENT_FORM, MISSING_DATE, MISSING_INSURANCE, MISSING_PI, MISSING_SECTION, MULTIPLE_REGISTRY_IDS, OTHER, REGISTRY_MISMATCH, CONSENT_GAP, ETHICS_GAP, FORMAT_ISSUE, METHOD_UNSPECIFIED, MISSING_SECTION, NO_DATA_MONITORING, NO_HARMS_PLAN, NO_PRIMARY_OUTCOME, NO_STOPPING_RULES, UNJUSTIFIED_SAMPLE_SIZE | 3 | 102,391 / 23,189 | 207.7 |
| Full system, reviewer and critic with tool use | nct01977547 | RETURNED_ADMIN (RETURNED_ADMIN) | 15 | 4 | 30 | 5/9 | OTHER, OTHER, OTHER, OTHER | ETHICS_GAP, FORMAT_ISSUE, INTERNAL_CONTRADICTION, MISSING_CONSENT_FORM, MISSING_DOCUMENT, MISSING_INSURANCE, MISSING_SECTION, MISSING_SIGNATURE_PAGE, MISSING_SPONSOR, REGISTRY_MISMATCH, CONSENT_GAP, ETHICS_GAP, FORMAT_ISSUE, INCONSISTENT_SAMPLE_SIZE, INTERNAL_CONTRADICTION, METHOD_UNSPECIFIED, MISSING_SECTION, NO_SAMPLE_SIZE_JUSTIFICATION, OTHER, REGISTRY_MISMATCH, SAFETY_GAP, UNJUSTIFIED_SAMPLE_SIZE | 6 | 1,086,751 / 81,687 | 716.9 |
| Full system, reviewer and critic with tool use | nct04084990 | RETURNED_ADMIN (RETURNED_ADMIN) | 15 | 5 | 30 | 7/9 | MISSING_REGISTRY_ID, MISSING_VERSION | CONSENT_GAP, ETHICS_GAP, FORMAT_ISSUE, INTERNAL_CONTRADICTION, MISSING_DOCUMENT, MISSING_INSURANCE, MISSING_SIGNATURE_PAGE, MISSING_SPONSOR, REGISTRY_MISMATCH, CONSENT_GAP, ETHICS_GAP, INTERNAL_CONTRADICTION, METHOD_UNSPECIFIED, MISSING_SECTION, NO_SAMPLE_SIZE_JUSTIFICATION, OTHER, REGISTRY_MISMATCH, SAFETY_GAP, UNJUSTIFIED_SAMPLE_SIZE | 6 | 537,274 / 75,565 | 662.4 |
| Full system, reviewer and critic with tool use | nct05199324 | RETURNED_ADMIN (RETURNED_ADMIN) | 12 | 1 | 31 | 7/9 | OTHER, OTHER | CONSENT_GAP, ETHICS_GAP, FORMAT_ISSUE, INTERNAL_CONTRADICTION, MISSING_DATE, MISSING_DOCUMENT, MISSING_INSURANCE, MISSING_SPONSOR, MULTIPLE_REGISTRY_IDS, OTHER, CONSENT_GAP, FORMAT_ISSUE, INCONSISTENT_SAMPLE_SIZE, INTERNAL_CONTRADICTION, METHOD_UNSPECIFIED, MISSING_SECTION, OTHER, RANDOMIZATION_METHOD_UNSPECIFIED, REGISTRY_MISMATCH, SAFETY_GAP, UNJUSTIFIED_SAMPLE_SIZE | 6 | 1,005,419 / 79,231 | 694.7 |
| Full system, reviewer and critic with tool use | nct05698277 | RETURNED_ADMIN (RETURNED_ADMIN) | 16 | 1 | 27 | 5/10 | INTERNAL_CONTRADICTION, MISSING_REGISTRY_ID, OTHER, OTHER, OTHER | CONSENT_GAP, FORMAT_ISSUE, INTERNAL_CONTRADICTION, MISSING_CONSENT_FORM, MISSING_ETHICS_STATEMENT, MISSING_INSURANCE, MISSING_SECTION, MISSING_SIGNATURE_PAGE, MISSING_SPONSOR, OTHER, REGISTRY_MISMATCH, CONSENT_GAP, ETHICS_GAP, FORMAT_ISSUE, INCONSISTENT_PHASE, INCONSISTENT_SAMPLE_SIZE, INTERNAL_CONTRADICTION, METHOD_UNSPECIFIED, MISSING_SECTION, NO_DATA_MONITORING, NO_SAMPLE_SIZE_JUSTIFICATION, NO_STOPPING_RULES, OTHER, SAFETY_GAP, UNJUSTIFIED_SAMPLE_SIZE | 6 | 664,656 / 78,401 | 698.8 |
| Full system, reviewer and critic with tool use | nct06846736 | RETURNED_ADMIN (RETURNED_ADMIN) | 22 | 6 | 27 | 6/9 | MISSING_REGISTRY_ID, OTHER, OTHER | CONSENT_GAP, ETHICS_GAP, FORMAT_ISSUE, INTERNAL_CONTRADICTION, MISSING_CONSENT_FORM, MISSING_DATE, MISSING_INSURANCE, MISSING_PI, MISSING_SECTION, MULTIPLE_REGISTRY_IDS, OTHER, REGISTRY_MISMATCH, CONSENT_GAP, ETHICS_GAP, METHOD_UNSPECIFIED, MISSING_SECTION, NO_DATA_MONITORING, NO_HARMS_PLAN, NO_PRIMARY_OUTCOME, NO_STOPPING_RULES, OTHER, REGISTRY_MISMATCH, UNJUSTIFIED_SAMPLE_SIZE | 6 | 360,774 / 73,424 | 644.9 |

## Reading the rows

1. **Single LLM call, no code verification** - one LLM call; the model's own status stands (unmarked findings count as verified). Measures how many of the model's claims a human would have to re-check.
2. **Single LLM call + code verification** - the same call; a quote the code cannot locate in the PDF or an unknown guideline code makes the finding unverified. This is the Single LLM call baseline of the charter.
3. **Full system without the critic** - administrative agent + scientific reviewer, code-only verification of the reviewer's findings, no revision round. Isolates the contribution of the agent split.
4. **Full system** - row 3 plus the Scientific Critic (verdict per finding, missed issues, at most one revision round). The difference between rows 3 and 4 is the critic's contribution.
## Scientific domain only (reduced-scope view)

Labels and predictions restricted to the scientific domain. The five labeled protocols are public registry documents without submission appendices; the labeler recorded what is wrong *in the protocol text*, not which package documents are absent, so this view compares like with like.

| # | Configuration | Precision of VERIFIED findings | Recall (coverage) of labeled findings | Unverified |
|---|---|---|---|---|
| 0 | Rules only (29 deterministic checks, no LLM) | 6% (1/16) | 3% (1/37) | 0 |
| 1 | Single LLM call, no code verification | 29% (19/66) | 57% (21/37) | 0 |
| 2 | Single LLM call + code verification | 25% (17/68) | 46% (17/37) | 0 |
| 3 | Full system without the critic | 33% (26/79) | 57% (21/37) | 9 |
| 4 | Full system (4 agents, critic, 1 revision round) | 34% (38/112) | 78% (29/37) | 50 |
| 2' | Single agent with tool use + code verification | 29% (7/24) | 49% (18/37) | 33 |
| 3' | Full system without the critic, reviewer with tool use | 31% (9/29) | 65% (24/37) | 47 |
| 4' | Full system, reviewer and critic with tool use | 36% (13/36) | 70% (26/37) | 113 |

| Configuration | Case | Verified | Matched verified | Unverified | Coverage | Missed labels |
|---|---|---|---|---|---|---|
| Rules only (29 deterministic checks, no LLM) | nct01977547 | 2 | 0 | 0 | 0/8 | INTERNAL_CONTRADICTION, INTERNAL_CONTRADICTION, METHOD_UNSPECIFIED, METHOD_UNSPECIFIED, OTHER, OTHER, OTHER, OTHER |
| Rules only (29 deterministic checks, no LLM) | nct04084990 | 3 | 1 | 0 | 1/7 | INTERNAL_CONTRADICTION, METHOD_UNSPECIFIED, METHOD_UNSPECIFIED, METHOD_UNSPECIFIED, OTHER, OTHER |
| Rules only (29 deterministic checks, no LLM) | nct05199324 | 2 | 0 | 0 | 0/9 | INTERNAL_CONTRADICTION, NO_DATA_MONITORING, OTHER, OTHER, OTHER, OTHER, OTHER, OTHER, OTHER |
| Rules only (29 deterministic checks, no LLM) | nct05698277 | 5 | 0 | 0 | 0/8 | INTERNAL_CONTRADICTION, INTERNAL_CONTRADICTION, METHOD_UNSPECIFIED, OTHER, OTHER, OTHER, OTHER, OTHER |
| Rules only (29 deterministic checks, no LLM) | nct06846736 | 4 | 0 | 0 | 0/5 | INTERNAL_CONTRADICTION, OTHER, OTHER, OTHER, OTHER |
| Single LLM call, no code verification | nct01977547 | 12 | 4 | 0 | 4/8 | INTERNAL_CONTRADICTION, METHOD_UNSPECIFIED, OTHER, OTHER |
| Single LLM call, no code verification | nct04084990 | 15 | 6 | 0 | 6/7 | OTHER |
| Single LLM call, no code verification | nct05199324 | 10 | 3 | 0 | 4/9 | OTHER, OTHER, OTHER, OTHER, OTHER |
| Single LLM call, no code verification | nct05698277 | 16 | 5 | 0 | 3/8 | OTHER, OTHER, OTHER, OTHER, OTHER |
| Single LLM call, no code verification | nct06846736 | 13 | 1 | 0 | 4/5 | INTERNAL_CONTRADICTION |
| Single LLM call + code verification | nct01977547 | 11 | 4 | 0 | 4/8 | OTHER, OTHER, OTHER, OTHER |
| Single LLM call + code verification | nct04084990 | 17 | 5 | 0 | 6/7 | OTHER |
| Single LLM call + code verification | nct05199324 | 10 | 2 | 0 | 3/9 | INTERNAL_CONTRADICTION, OTHER, OTHER, OTHER, OTHER, OTHER |
| Single LLM call + code verification | nct05698277 | 17 | 5 | 0 | 3/8 | OTHER, OTHER, OTHER, OTHER, OTHER |
| Single LLM call + code verification | nct06846736 | 13 | 1 | 0 | 1/5 | OTHER, OTHER, OTHER, OTHER |
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
| Single agent with tool use + code verification | nct01977547 | 4 | 2 | 6 | 5/8 | METHOD_UNSPECIFIED, OTHER, OTHER |
| Single agent with tool use + code verification | nct04084990 | 5 | 2 | 9 | 5/7 | METHOD_UNSPECIFIED, METHOD_UNSPECIFIED |
| Single agent with tool use + code verification | nct05199324 | 3 | 1 | 7 | 4/9 | INTERNAL_CONTRADICTION, NO_DATA_MONITORING, OTHER, OTHER, OTHER |
| Single agent with tool use + code verification | nct05698277 | 7 | 1 | 6 | 3/8 | OTHER, OTHER, OTHER, OTHER, OTHER |
| Single agent with tool use + code verification | nct06846736 | 5 | 1 | 5 | 1/5 | OTHER, OTHER, OTHER, OTHER |
| Full system without the critic, reviewer with tool use | nct01977547 | 7 | 4 | 8 | 7/8 | OTHER |
| Full system without the critic, reviewer with tool use | nct04084990 | 5 | 2 | 13 | 6/7 | METHOD_UNSPECIFIED |
| Full system without the critic, reviewer with tool use | nct05199324 | 5 | 1 | 9 | 5/9 | OTHER, OTHER, OTHER, OTHER |
| Full system without the critic, reviewer with tool use | nct05698277 | 7 | 1 | 8 | 3/8 | METHOD_UNSPECIFIED, OTHER, OTHER, OTHER, OTHER |
| Full system without the critic, reviewer with tool use | nct06846736 | 5 | 1 | 9 | 3/5 | OTHER, OTHER |
| Full system, reviewer and critic with tool use | nct01977547 | 7 | 3 | 23 | 4/8 | OTHER, OTHER, OTHER, OTHER |
| Full system, reviewer and critic with tool use | nct04084990 | 9 | 5 | 21 | 7/7 | - |
| Full system, reviewer and critic with tool use | nct05199324 | 5 | 1 | 26 | 7/9 | OTHER, OTHER |
| Full system, reviewer and critic with tool use | nct05698277 | 8 | 1 | 22 | 5/8 | OTHER, OTHER, OTHER |
| Full system, reviewer and critic with tool use | nct06846736 | 7 | 3 | 21 | 3/5 | OTHER, OTHER |


## Uncertainty: protocol-level bootstrap (B=2000, seed 20261108, 5 protocols)

The five labeled protocols are resampled with replacement; precision and recall are pooled on each resample. A gap whose 95% interval includes zero (or whose `P(gap <= 0)` is large) is not distinguishable from noise on this test set. One model run per row: run-to-run variation of the model is not separated from protocol variation here.

| Row | Precision 95% CI (all) | Recall 95% CI (all) | Precision 95% CI (scientific) | Recall 95% CI (scientific) |
|---|---|---|---|---|
| 0 Rules only (29 deterministic checks, no LLM) | 0% - 16% | 0% - 20% | 0% - 20% | 0% - 9% |
| 1 Single LLM call, no code verification | 15% - 23% | 43% - 67% | 17% - 37% | 44% - 75% |
| 2 Single LLM call + code verification | 14% - 21% | 38% - 56% | 15% - 32% | 30% - 68% |
| 3 Full system without the critic | 15% - 24% | 35% - 71% | 22% - 42% | 33% - 83% |
| 4 Full system (4 agents, critic, 1 revision round) | 18% - 29% | 66% - 82% | 22% - 45% | 66% - 91% |
| 2' Single agent with tool use + code verification | 11% - 24% | 38% - 53% | 18% - 43% | 33% - 63% |
| 3' Full system without the critic, reviewer with tool use | 10% - 24% | 44% - 73% | 17% - 48% | 49% - 83% |
| 4' Full system, reviewer and critic with tool use | 12% - 29% | 55% - 76% | 21% - 49% | 55% - 85% |

| Gap | View | Precision gap: mean (95% CI), P(gap <= 0) | Recall gap: mean (95% CI), P(gap <= 0) |
|---|---|---|---|
| 4 vs 1 | all | 4% (0% to 9%), P=0.01 | 20% (4% to 35%), P=0.01 |
| 4 vs 2 | all | 6% (2% to 9%), P=0.00 | 28% (17% to 40%), P=0.00 |
| 4 vs 3 | all | 4% (-0% to 7%), P=0.07 | 19% (7% to 38%), P=0.00 |
| 4' vs 1 | all | 2% (-9% to 11%), P=0.36 | 11% (-2% to 24%), P=0.03 |
| 4' vs 2 | all | 4% (-7% to 12%), P=0.22 | 20% (11% to 31%), P=0.00 |
| 4' vs 3 | all | 1% (-8% to 9%), P=0.37 | 10% (-11% to 36%), P=0.20 |
| 4' vs 4 | all | -2% (-15% to 8%), P=0.61 | -9% (-22% to 0%), P=1.00 |
| 4' vs 2' | all | 4% (0% to 6%), P=0.02 | 19% (9% to 28%), P=0.00 |
| 4' vs 3' | all | 4% (-1% to 9%), P=0.07 | 6% (-9% to 19%), P=0.24 |
| 3' vs 1 | all | -2% (-12% to 7%), P=0.62 | 5% (-8% to 20%), P=0.33 |
| 3' vs 2 | all | -0% (-9% to 8%), P=0.48 | 13% (0% to 27%), P=0.05 |
| 3' vs 3 | all | -3% (-10% to 2%), P=0.71 | 4% (-6% to 17%), P=0.34 |
| 3' vs 4 | all | -6% (-16% to 1%), P=0.90 | -15% (-23% to -7%), P=1.00 |
| 3' vs 2' | all | -0% (-4% to 4%), P=0.59 | 13% (6% to 20%), P=0.00 |
| 2' vs 1 | all | -2% (-11% to 7%), P=0.61 | -9% (-22% to 2%), P=0.94 |
| 2' vs 2 | all | 0% (-10% to 7%), P=0.44 | 0% (-8% to 9%), P=0.58 |
| 2' vs 3 | all | -2% (-10% to 4%), P=0.68 | -9% (-20% to 7%), P=0.92 |
| 2' vs 4 | all | -6% (-17% to 4%), P=0.84 | -28% (-33% to -24%), P=1.00 |
| 4 vs 1 | scientific | 5% (-1% to 12%), P=0.07 | 21% (3% to 33%), P=0.01 |
| 4 vs 2 | scientific | 9% (6% to 13%), P=0.00 | 32% (22% to 41%), P=0.00 |
| 4 vs 3 | scientific | 1% (-6% to 8%), P=0.38 | 21% (3% to 42%), P=0.01 |
| 4' vs 1 | scientific | 8% (-9% to 23%), P=0.20 | 13% (-3% to 27%), P=0.08 |
| 4' vs 2 | scientific | 11% (-6% to 26%), P=0.10 | 24% (8% to 39%), P=0.00 |
| 4' vs 3 | scientific | 3% (-11% to 17%), P=0.31 | 12% (-19% to 42%), P=0.23 |
| 4' vs 4 | scientific | 2% (-18% to 20%), P=0.38 | -8% (-24% to 0%), P=1.00 |
| 4' vs 2' | scientific | 6% (-5% to 17%), P=0.13 | 22% (3% to 34%), P=0.01 |
| 4' vs 3' | scientific | 5% (-8% to 18%), P=0.22 | 5% (-19% to 22%), P=0.36 |
| 3' vs 1 | scientific | 3% (-12% to 19%), P=0.41 | 8% (-6% to 24%), P=0.20 |
| 3' vs 2 | scientific | 6% (-7% to 19%), P=0.20 | 19% (5% to 34%), P=0.01 |
| 3' vs 3 | scientific | -2% (-12% to 6%), P=0.61 | 8% (0% to 22%), P=0.33 |
| 3' vs 4 | scientific | -3% (-18% to 10%), P=0.65 | -13% (-22% to -3%), P=1.00 |
| 3' vs 2' | scientific | 1% (-6% to 8%), P=0.40 | 17% (7% to 28%), P=0.00 |
| 2' vs 1 | scientific | 1% (-10% to 12%), P=0.40 | -9% (-29% to 5%), P=0.88 |
| 2' vs 2 | scientific | 5% (-7% to 13%), P=0.24 | 3% (-6% to 10%), P=0.38 |
| 2' vs 3 | scientific | -3% (-13% to 8%), P=0.70 | -9% (-27% to 10%), P=0.87 |
| 2' vs 4 | scientific | -4% (-19% to 5%), P=0.66 | -30% (-34% to -26%), P=1.00 |


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
