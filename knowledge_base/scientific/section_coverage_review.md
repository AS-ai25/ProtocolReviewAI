# Scientific Protocol Section Coverage — advisory screen v1.0

## Scope
This screening addendum covers **presence and substantive adequacy** of protocol components. It is intentionally separate from administrative **submission-package** checks (ICF/insurance forms etc.). The 2025 SPIRIT checklist covers **randomised trial protocols**: do not universally apply randomisation/blinding requirements to observational or single-arm designs. A section can be present without satisfying the reporting item, and information can be present without a dedicated heading.

## Mandatory review workflow
1. Identify trial design; determine applicability of each item.
2. Screen headings and in-text mentions; verify contents manually / with Scientific Reviewer.
3. Check both **inclusion and exclusion** independently; confirm eligibility criteria are operational, consistent and applicable to the population.
4. For each *potentially missing* item: inspect appendices and tables; do not infer absence from a keyword scan.
5. Record N/A, described, potentially missing, insufficient detail, or contradictory with supporting page evidence. Only supported findings advance to Scientific Critic; the final committee decision remains human.

## Screened topics / validated SPIRIT 2025 linkage
| Topic | Official 2025 item | Substance to review |
|---|---|---|
| Background and rationale | 9a | Scientific justification, previous evidence and comparator rationale |
| Objectives | 10 | Specific hypothesis/objectives |
| Design | 12 | Trial design and allocation framework |
| Inclusion criteria | 14a | Explicit eligibility, age, population, clinical thresholds if appropriate |
| Exclusion criteria | 14a | Explicit exclusions and safety/risk logic; applicability |
| Intervention/comparator | 15a | Dose, administration, arms, schedules, reproducibility |
| Outcomes | 16 | Primary and secondary variables, assessment methods, timepoints |
| Harms | 17 | Harm definitions and assessment approach |
| Timeline | 18 | Visits, follow-up, enrolment, schedule of assessments |
| Sample size | 19 | Assumptions, power, effect size and attrition where relevant |
| Randomisation | 21a | Sequence generation only if randomised |
| Blinding | 24a | Whom/how blinded; applicability to open-label design |
| Data management | 26 | Data entry, security, quality and storage |
| Statistical methods | 27a | Primary and secondary analyses, estimands where relevant |
| Ethics | 30 | Ethics review plan |
| Consent | 32a | How informed consent is obtained, including responsible personnel |

The table is a **selected screening subset**, not a full SPIRIT 2025 checklist. The complete 34-item checklist with subitems must be assessed separately for a full SPIRIT conformity statement. Item identifiers were checked against the SPIRIT 2025 official table; applicability and protocol evidence still require professional review.

## How to interpret
- `heading_detected`: a probable heading exists; content adequacy NOT established.
- `mentioned_only`: only a keyword mention was detected; inspect the text.
- `needs_manual_review`: not detected by this heuristic; **NOT** an automatically verified omission.
- `not_applicable`: known design makes item inapplicable (if randomized=False was supplied).

## Baseline integrity
This addendum is injected **only into the Scientific Reviewer prompt** as review context. It does not modify scores, deterministic findings, administrative gates, critic authority, or existing baselines. To include this intervention in scientific claims comparing single- and multi-agent performance, run a new equal-input ablation version and document it.

## Sources
- SPIRIT 2025 official BMJ statement: https://www.bmj.com/content/389/bmj-2024-081477
- SPIRIT 2025 explanation: https://www.bmj.com/content/389/bmj-2024-081660
- GCP lecture 3 (user-provided), discussion of protocol required information, inclusion/exclusion, endpoints, timetable and statistical rationale; historical course resource, not a current legal mandate.
