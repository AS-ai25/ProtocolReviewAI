# Evaluation results - ablation (Checkpoint 2)

Generated 2026-10-21 09:53 by `eval/ablation.py` **--no-llm (DRY RUN: MockLLM, no API calls - harness check only, not results)**.
Test set: 2 labeled case(s) - `synthetic_flawed` (10 labels), `synthetic_good` (0 labels).
All rows run with the evaluation gate bypass (`force_scientific`): the scientific stage runs even when the administrative gate fails; the decision stays RETURNED_ADMIN in that case.

## Ablation table

| # | Configuration | Precision of VERIFIED findings | Recall (coverage) of labeled findings | Unverified | LLM calls | Tokens in / out | Runtime |
|---|---|---|---|---|---|---|---|
| 1 | Single agent, no code verification | 100% (11/11) | 100% (10/10) | 0 | 2 | 0 / 0 | 0 s |
| 2 | Single agent + code verification | 100% (11/11) | 100% (10/10) | 0 | 2 | 0 / 0 | 0 s |
| 3 | Full system without the critic | 100% (11/11) | 100% (10/10) | 0 | 6 | 0 / 0 | 1 s |
| 4 | Full system (4 agents, critic, 1 revision round) | 100% (11/11) | 100% (10/10) | 0 | 6 | 0 / 0 | 0 s |

Primary metric (charter v1.4, locked): precision of verified findings against blind human labels on the real-protocol test set, with recall of labeled findings as the companion metric. Unverified findings are routed to a human and counted separately, not as claims.

Matching rule: a predicted finding matches a labeled one when the domain matches and (the categories are the same or aliases in `eval/category_aliases.json`, OR the guideline reference is the same and the page is within +-1). Rejected and withdrawn findings are not predictions.

## Per case

| Configuration | Case | Decision (expected) | Verified | Matched verified | Unverified | Coverage | Missed labels | Unlabeled reported | Calls | Tokens in / out | s |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Single agent, no code verification | synthetic_flawed | RETURNED_ADMIN (RETURNED_ADMIN) | 11 | 11 | 0 | 10/10 | - | - | 1 | 0 / 0 | 0.1 |
| Single agent, no code verification | synthetic_good | PASS (PASS) | 0 | 0 | 0 | 0/0 | - | - | 1 | 0 / 0 | 0.0 |
| Single agent + code verification | synthetic_flawed | RETURNED_ADMIN (RETURNED_ADMIN) | 11 | 11 | 0 | 10/10 | - | - | 1 | 0 / 0 | 0.0 |
| Single agent + code verification | synthetic_good | PASS (PASS) | 0 | 0 | 0 | 0/0 | - | - | 1 | 0 / 0 | 0.0 |
| Full system without the critic | synthetic_flawed | RETURNED_ADMIN (RETURNED_ADMIN) | 11 | 11 | 0 | 10/10 | - | - | 3 | 0 / 0 | 0.7 |
| Full system without the critic | synthetic_good | PASS (PASS) | 0 | 0 | 0 | 0/0 | - | - | 3 | 0 / 0 | 0.1 |
| Full system (4 agents, critic, 1 revision round) | synthetic_flawed | RETURNED_ADMIN (RETURNED_ADMIN) | 11 | 11 | 0 | 10/10 | - | - | 3 | 0 / 0 | 0.2 |
| Full system (4 agents, critic, 1 revision round) | synthetic_good | PASS (PASS) | 0 | 0 | 0 | 0/0 | - | - | 3 | 0 / 0 | 0.1 |

## Reading the rows

1. **Single agent, no code verification** - one LLM call; the model's own status stands (unmarked findings count as verified). Measures how many of the model's claims a human would have to re-check.
2. **Single agent + code verification** - the same call; a quote the code cannot locate in the PDF or an unknown guideline code makes the finding unverified. This is the Single-Agent Baseline of the charter.
3. **Full system without the critic** - administrative agent + scientific reviewer, code-only verification of the reviewer's findings, no revision round. Isolates the contribution of the agent split.
4. **Full system** - row 3 plus the Scientific Critic (verdict per finding, missed issues, at most one revision round). The difference between rows 3 and 4 is the critic's contribution.

> DRY RUN: every LLM answer is the empty MockLLM response, so only the deterministic rule findings appear and the four rows are expected to be identical. Run without `--no-llm` for the real table.
