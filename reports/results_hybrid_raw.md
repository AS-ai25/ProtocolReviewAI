# Evaluation results - ablation (Checkpoint 2)

Generated 2026-11-13 12:57 by `eval/ablation.py`, model `claude-opus-5-5`.
Test set: 5 labeled case(s) - `nct01977547` (9 labels), `nct04084990` (9 labels), `nct05199324` (9 labels), `nct05698277` (10 labels), `nct06846736` (9 labels).
All rows run with the evaluation gate bypass (`force_scientific`): the scientific stage runs even when the administrative gate fails; the decision stays RETURNED_ADMIN in that case.

## Ablation table

| # | Configuration | Precision of VERIFIED findings | Recall (coverage) of labeled findings | Unverified | LLM calls | Tokens in / out | Runtime |
|---|---|---|---|---|---|---|---|
| 4-M | Full system, current code, Opus for the scientific agents, Sonnet for the coordinator and the administrative agent | 22% (16/74) | 80% (37/46) | 141 | 30 | 1,506,934 / 260,314 | 2212 s |

Primary metric (charter v1.4, locked): precision of verified findings against blind human labels on the real-protocol test set, with recall of labeled findings as the companion metric. Unverified findings are routed to a human and counted separately, not as claims.

Matching rule: a predicted finding matches a labeled one when the domain matches and (the categories are the same or aliases in `eval/category_aliases.json`, OR the guideline reference is the same and the page is within +-1). Rejected and withdrawn findings are not predictions.

## Per case

| Configuration | Case | Decision (expected) | Verified | Matched verified | Unverified | Coverage | Missed labels | Unlabeled reported | Calls | Tokens in / out | s |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Full system, current code, Opus for the scientific agents, Sonnet for the coordinator and the administrative agent | nct01977547 | RETURNED_ADMIN (RETURNED_ADMIN) | 14 | 2 | 29 | 7/9 | OTHER, OTHER | INTERNAL_CONTRADICTION, MISSING_CONSENT_FORM, MISSING_DOCUMENT, MISSING_INSURANCE, MISSING_SECTION, MISSING_SIGNATURE_PAGE, MISSING_SPONSOR, CONSENT_GAP, ETHICS_GAP, FORMAT_ISSUE, INCONSISTENT_SAMPLE_SIZE, INTERNAL_CONTRADICTION, METHOD_UNSPECIFIED, MISSING_SECTION, NO_SAMPLE_SIZE_JUSTIFICATION, OTHER, REGISTRY_MISMATCH, SAFETY_GAP, UNJUSTIFIED_SAMPLE_SIZE | 6 | 480,146 / 67,752 | 573.1 |
| Full system, current code, Opus for the scientific agents, Sonnet for the coordinator and the administrative agent | nct04084990 | RETURNED_ADMIN (RETURNED_ADMIN) | 10 | 3 | 37 | 7/9 | MISSING_REGISTRY_ID, MISSING_VERSION | ETHICS_GAP, FORMAT_ISSUE, INTERNAL_CONTRADICTION, MISSING_DOCUMENT, MISSING_INSURANCE, MISSING_SECTION, MISSING_SIGNATURE_PAGE, MISSING_SPONSOR, REGISTRY_MISMATCH, CONSENT_GAP, ETHICS_GAP, FORMAT_ISSUE, INTERNAL_CONTRADICTION, METHOD_UNSPECIFIED, MISSING_SECTION, NO_SAMPLE_SIZE_JUSTIFICATION, OTHER, REGISTRY_MISMATCH, SAFETY_GAP, UNJUSTIFIED_SAMPLE_SIZE | 6 | 275,721 / 63,885 | 528.0 |
| Full system, current code, Opus for the scientific agents, Sonnet for the coordinator and the administrative agent | nct05199324 | RETURNED_ADMIN (RETURNED_ADMIN) | 12 | 1 | 26 | 6/9 | OTHER, OTHER, OTHER | FORMAT_ISSUE, INTERNAL_CONTRADICTION, MISSING_DATE, MISSING_DOCUMENT, MISSING_INSURANCE, MISSING_SPONSOR, MULTIPLE_REGISTRY_IDS, OTHER, CONSENT_GAP, ETHICS_GAP, INCONSISTENT_SAMPLE_SIZE, INTERNAL_CONTRADICTION, METHOD_UNSPECIFIED, MISSING_SECTION, OTHER, RANDOMIZATION_METHOD_UNSPECIFIED, REGISTRY_MISMATCH, SAFETY_GAP, UNJUSTIFIED_SAMPLE_SIZE | 6 | 323,055 / 41,383 | 356.0 |
| Full system, current code, Opus for the scientific agents, Sonnet for the coordinator and the administrative agent | nct05698277 | RETURNED_ADMIN (RETURNED_ADMIN) | 15 | 3 | 28 | 9/10 | MISSING_REGISTRY_ID | FORMAT_ISSUE, INTERNAL_CONTRADICTION, MISSING_CONSENT_FORM, MISSING_DOCUMENT, MISSING_ETHICS_STATEMENT, MISSING_INSURANCE, MISSING_SIGNATURE_PAGE, MISSING_SPONSOR, CONSENT_GAP, ETHICS_GAP, FORMAT_ISSUE, INCONSISTENT_PHASE, INCONSISTENT_SAMPLE_SIZE, INTERNAL_CONTRADICTION, METHOD_UNSPECIFIED, MISSING_SECTION, NO_DATA_MONITORING, NO_SAMPLE_SIZE_JUSTIFICATION, NO_STOPPING_RULES, OTHER, REGISTRY_MISMATCH, SAFETY_GAP, UNJUSTIFIED_SAMPLE_SIZE | 6 | 271,400 / 49,664 | 429.5 |
| Full system, current code, Opus for the scientific agents, Sonnet for the coordinator and the administrative agent | nct06846736 | RETURNED_ADMIN (RETURNED_ADMIN) | 23 | 7 | 21 | 8/9 | MISSING_REGISTRY_ID | CONSENT_GAP, FORMAT_ISSUE, INTERNAL_CONTRADICTION, MISSING_CONSENT_FORM, MISSING_DATE, MISSING_INSURANCE, MISSING_PI, MISSING_SECTION, MULTIPLE_REGISTRY_IDS, REGISTRY_MISMATCH, CONSENT_GAP, ETHICS_GAP, FORMAT_ISSUE, METHOD_UNSPECIFIED, MISSING_SECTION, NO_DATA_MONITORING, NO_HARMS_PLAN, NO_PRIMARY_OUTCOME, NO_STOPPING_RULES, OTHER, REGISTRY_MISMATCH, UNJUSTIFIED_SAMPLE_SIZE | 6 | 156,612 / 37,630 | 325.3 |

## Reading the rows

1. **Single LLM call, no code verification** - one LLM call; the model's own status stands (unmarked findings count as verified). Measures how many of the model's claims a human would have to re-check.
2. **Single LLM call + code verification** - the same call; a quote the code cannot locate in the PDF or an unknown guideline code makes the finding unverified. This is the Single LLM call baseline of the charter.
3. **Full system without the critic** - administrative agent + scientific reviewer, code-only verification of the reviewer's findings, no revision round. Isolates the contribution of the agent split.
4. **Full system** - row 3 plus the Scientific Critic (verdict per finding, missed issues, at most one revision round). The difference between rows 3 and 4 is the critic's contribution.
