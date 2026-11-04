# Knowledge base versions

| Version | Date | Commit / tag | Content | Used by |
|---|---|---|---|---|
| kb-v1 | 2026-10-21 | tag `kb-v1` | team draft: ADMIN-CHK-01..15, SPIRIT 2025 items with a legacy-code compatibility list, GCP-01..12, section-coverage screen; verification banners | ablation run `20261029-205913` (`reports/results.md`), all four rows; its guideline-code set is kept in `eval/results/kb-v1-codes.json` |
| kb-v2 | 2026-11-04 | tag `kb-v2` | Ron's verified revision: every code and its order unchanged; applicability addenda per code and per study design (interventional / observational / retrospective / questionnaire / AI model), protocol-only vs submission-package guidance, source hierarchy (MoH Procedure 14, Helsinki 2024, ICH E6(R3), E8(R1), SPIRIT 2025, STROBE); legacy compatibility list removed; banners removed | no evaluation run yet - metrics attributed to kb-v2 require a new run |

Rules: identifiers and their order never change inside a version; any content change gets a new version and tag;
evaluation results always name the version they were run with.
