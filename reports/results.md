# Evaluation results - ablation (Checkpoint 2)

Generated 2026-10-21 09:57 by `eval/ablation.py`, model `claude-opus-5-5`.
Test set: 2 labeled case(s) - `synthetic_flawed` (10 labels), `synthetic_good` (0 labels).
All rows run with the evaluation gate bypass (`force_scientific`): the scientific stage runs even when the administrative gate fails; the decision stays RETURNED_ADMIN in that case.

## Ablation table

| # | Configuration | Precision of VERIFIED findings | Recall (coverage) of labeled findings | Unverified | LLM calls | Tokens in / out | Runtime |
|---|---|---|---|---|---|---|---|
| 1 | Single agent, no code verification | 32% (12/37) | 100% (10/10) | 0 | 2 | 24,112 / 19,208 | 167 s |
| 2 | Single agent + code verification | 36% (12/33) | 100% (10/10) | 2 | 2 | 24,112 / 17,639 | 154 s |
| 3 | Full system without the critic | 25% (12/48) | 100% (10/10) | 5 | 6 | 58,473 / 28,773 | 282 s |
| 4 | Full system (4 agents, critic, 1 revision round) | 18% (12/67) | 100% (10/10) | 18 | 12 | 177,856 / 74,166 | 669 s |

Primary metric (charter v1.4, locked): precision of verified findings against blind human labels on the real-protocol test set, with recall of labeled findings as the companion metric. Unverified findings are routed to a human and counted separately, not as claims.

Matching rule: a predicted finding matches a labeled one when the domain matches and (the categories are the same or aliases in `eval/category_aliases.json`, OR the guideline reference is the same and the page is within +-1). Rejected and withdrawn findings are not predictions.

## Per case

| Configuration | Case | Decision (expected) | Verified | Matched verified | Unverified | Coverage | Missed labels | Unlabeled reported | Calls | Tokens in / out | s |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Single agent, no code verification | synthetic_flawed | RETURNED_ADMIN (RETURNED_ADMIN) | 25 | 12 | 0 | 10/10 | - | FORMAT_ISSUE, MISSING_DOCUMENT, REGISTRY_MISMATCH, CONSENT_GAP, ETHICS_GAP, INTERNAL_CONTRADICTION, METHOD_UNSPECIFIED, MISSING_SECTION, REGISTRY_MISMATCH, SAFETY_GAP | 1 | 13,041 / 9,671 | 85.4 |
| Single agent, no code verification | synthetic_good | RETURNED_ADMIN (PASS) | 12 | 0 | 0 | 0/0 | - | MISSING_DOCUMENT, REGISTRY_MISMATCH, CONSENT_GAP, ETHICS_GAP, METHOD_UNSPECIFIED, MISSING_DOCUMENT, REGISTRY_MISMATCH, SAFETY_GAP | 1 | 11,071 / 9,537 | 81.8 |
| Single agent + code verification | synthetic_flawed | RETURNED_ADMIN (RETURNED_ADMIN) | 22 | 12 | 1 | 10/10 | - | FORMAT_ISSUE, MISSING_DOCUMENT, REGISTRY_MISMATCH, ETHICS_GAP, INTERNAL_CONTRADICTION, METHOD_UNSPECIFIED, MISSING_SECTION, REGISTRY_MISMATCH, SAFETY_GAP | 1 | 13,041 / 8,739 | 79.8 |
| Single agent + code verification | synthetic_good | RETURNED_ADMIN (PASS) | 11 | 0 | 1 | 0/0 | - | MISSING_DOCUMENT, REGISTRY_MISMATCH, CONSENT_GAP, ETHICS_GAP, METHOD_UNSPECIFIED, REGISTRY_MISMATCH, SAFETY_GAP | 1 | 11,071 / 8,900 | 74.4 |
| Full system without the critic | synthetic_flawed | RETURNED_ADMIN (RETURNED_ADMIN) | 34 | 12 | 3 | 10/10 | - | ETHICS_GAP, FORMAT_ISSUE, INTERNAL_CONTRADICTION, MISSING_DOCUMENT, REGISTRY_MISMATCH, CONSENT_GAP, ETHICS_GAP, FORMAT_ISSUE, INTERNAL_CONTRADICTION, METHOD_UNSPECIFIED, MISSING_DOCUMENT, MISSING_SECTION, REGISTRY_MISMATCH, SAFETY_GAP | 3 | 32,934 / 16,227 | 147.1 |
| Full system without the critic | synthetic_good | RETURNED_ADMIN (PASS) | 14 | 0 | 2 | 0/0 | - | MISSING_DOCUMENT, REGISTRY_MISMATCH, CONSENT_GAP, ETHICS_GAP, METHOD_UNSPECIFIED, MISSING_DOCUMENT, MISSING_SECTION, REGISTRY_MISMATCH, SAFETY_GAP | 3 | 25,539 / 12,546 | 135.1 |
| Full system (4 agents, critic, 1 revision round) | synthetic_flawed | RETURNED_ADMIN (RETURNED_ADMIN) | 40 | 12 | 8 | 10/10 | - | ETHICS_GAP, FORMAT_ISSUE, INTERNAL_CONTRADICTION, MISSING_DOCUMENT, REGISTRY_MISMATCH, CONSENT_GAP, ETHICS_GAP, FORMAT_ISSUE, INTERNAL_CONTRADICTION, METHOD_UNSPECIFIED, MISSING_SECTION, OTHER, REGISTRY_MISMATCH, SAFETY_GAP, UNJUSTIFIED_SAMPLE_SIZE | 6 | 92,130 / 37,937 | 330.3 |
| Full system (4 agents, critic, 1 revision round) | synthetic_good | RETURNED_ADMIN (PASS) | 27 | 0 | 10 | 0/0 | - | CONSENT_GAP, FORMAT_ISSUE, INTERNAL_CONTRADICTION, MISSING_DOCUMENT, REGISTRY_MISMATCH, CONSENT_GAP, ETHICS_GAP, METHOD_UNSPECIFIED, MISSING_DOCUMENT, MISSING_SECTION, OTHER, REGISTRY_MISMATCH, SAFETY_GAP | 6 | 85,726 / 36,229 | 338.6 |

## Reading the rows

1. **Single agent, no code verification** - one LLM call; the model's own status stands (unmarked findings count as verified). Measures how many of the model's claims a human would have to re-check.
2. **Single agent + code verification** - the same call; a quote the code cannot locate in the PDF or an unknown guideline code makes the finding unverified. This is the Single-Agent Baseline of the charter.
3. **Full system without the critic** - administrative agent + scientific reviewer, code-only verification of the reviewer's findings, no revision round. Isolates the contribution of the agent split.
4. **Full system** - row 3 plus the Scientific Critic (verdict per finding, missed issues, at most one revision round). The difference between rows 3 and 4 is the critic's contribution.
