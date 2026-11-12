# Delivery notes for Amir | 12 November 2026

## Files
- `verified_findings_check_finding_correct_COMPLETED.csv`: original 30 findings, claim correctness check.
- `unmatched_verified_check_COMPLETED.csv`: 40 unmatched verified findings, with annotations.
- `verified_findings_check_v17_tools_REVIEWED.csv`: 30 tool-calling findings, with evidence and claim annotations.
- `unmatched_verified_check_reference.csv`: the original 38 matched reference findings.
- `unmatched_40_REFERENCE_CROSSCHECK_ACTION_REVIEWED.xlsx`: separate crosscheck and action notes; **not** a replacement for the raw annotation CSV.
- `HUMAN_REVIEW_PRESUBMISSION_AUDIT_REVISED.md`: quality flags, scope and caveats.
- `BUSINESS_VALUE_HYPOTHESIS.md`: preliminary business case for Git.

## Integrity checks
- CSV annotation rows: 30 / 40 / 30; mandatory annotations present.
- The first 11 original columns of the 40-finding file match the original raw CSV exactly.
- No original blind manual label file has been edited in this package.
- The checked copies are preserved; no annotation values were silently rewritten.

## 40 findings: reviewer classifications
- true but unlabeled: 31
- wrong: 5
- cannot tell: 4
- duplicate of a matched finding: 0

## Caveats
Five reference pairs were flagged as thematic overlaps and reviewed. No confirmed
full duplicate was established. This does not exclude partial overlap within
multi-part findings or constitute independent clinical adjudication. The
crosscheck spreadsheet is a supplemental reviewer document; do not import its
ACTION column as ground-truth labels.

The 2-3 hours/protocol figure is a team assumption about combined review
effort, not measured net time saved. Neither improved approval throughput nor
incremental hospital revenue has been demonstrated.
