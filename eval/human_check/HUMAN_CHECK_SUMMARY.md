# Human Evidence Check - 30 Findings

## Scope and method

A post-ablation human evidence check was completed on 30 system-generated findings sampled from five evaluation-set protocols. For each finding, the reviewer checked the quoted passage against the physical PDF page, reviewed its surrounding context, and assessed whether it supports the issue associated with the stated guideline reference. The original system output columns were preserved. The check was performed separately from the already committed blind manual labels.

**Interpretation:** `yes` = the cited passage supports the flagged issue; `partly` = the passage is relevant but supports only a narrower concern; `no` = the passage does not support the flagged issue or is absent from the referenced PDF page. These labels assess **evidence support**, not overall protocol quality or system precision.

## Results

| Assessment | Count | Percent |
|---|---:|---:|
| yes | 1 | 3.3% |
| partly | 5 | 16.7% |
| no | 24 | 80.0% |
| **Total** | **30** | **100%** |

| Protocol | yes | partly | no | total |
|---|---:|---:|---:|---:|
| ABC PICU (`nct01977547`) | 0 | 1 | 5 | 6 |
| SAFER (`nct04084990`) | 0 | 1 | 5 | 6 |
| INVEST (`nct05199324`) | 0 | 1 | 5 | 6 |
| Fetal cardiac (`nct05698277`) | 1 | 1 | 4 | 6 |
| ALK digital pathology (`nct06846736`) | 0 | 1 | 5 | 6 |

## Findings assessed as no

The following 24 system-generated findings received `no`. For the exact system quote and the reviewer's Hebrew rationale, use the corresponding `finding_id` + `case_id` in `verified_findings_check.csv`.

| case_id | finding_id | PDF page | guideline_ref |
|---|---|---:|---|
| `nct01977547` | `ADM-L002` | 1 | `ADMIN-CHK-02` |
| `nct01977547` | `ADM-L011` | 24 | `ADMIN-CHK-13` |
| `nct01977547` | `SCI-L004` | 21 | `GCP-07` |
| `nct01977547` | `SCI-L015` | 24 | `SPIRIT-3c` |
| `nct01977547` | `SCI-R001` | 3 | `SPIRIT-19` |
| `nct04084990` | `ADM-L005` | 18 | `ADMIN-CHK-08` |
| `nct04084990` | `SCI-L002` | 6 | `SPIRIT-22` |
| `nct04084990` | `SCI-L015` | 11 | `SPIRIT-33` |
| `nct04084990` | `SCI-L021` | 12 | `SPIRIT-27d` |
| `nct04084990` | `SCI-R091` | 6 | `SPIRIT-4` |
| `nct05199324` | `ADM-L003` | 27 | `ADMIN-CHK-15` |
| `nct05199324` | `SCI-L004` | 26 | `SPIRIT-28b; SPIRIT-28a` |
| `nct05199324` | `SCI-L007` | 7 | `SPIRIT-14a` |
| `nct05199324` | `SCI-L010` | 24 | `SPIRIT-15a` |
| `nct05199324` | `SCI-L023` | 17 | `SPIRIT-20` |
| `nct05698277` | `ADM-L005` | 8 | `ADMIN-CHK-15` |
| `nct05698277` | `SCI-L003` | 8 | `SPIRIT-27b` |
| `nct05698277` | `SCI-L016` | 8 | `SPIRIT-14a` |
| `nct05698277` | `SCI-R005` | 5 | `SPIRIT-8` |
| `nct06846736` | `ADM-L003` | 4 | `ADMIN-CHK-06` |
| `nct06846736` | `ADM-L006` | 1 | `ADMIN-CHK-10` |
| `nct06846736` | `ADM-L007` | 1 | `ADMIN-CHK-13` |
| `nct06846736` | `SCI-L013` | 4 | `SPIRIT-14a` |
| `nct06846736` | `SCI-L014` | 5 | `SPIRIT-27a` |

## Observed evidence-quality issues

- Quoted text sometimes documents a present or valid protocol element rather than the alleged deficiency.
- Some quotes are truncated, taken from the table of contents, or mapped to a guideline item they do not establish.
- Some methodological concerns are supported only partly by the cited passage and require the wider protocol context.
- Applicability of trial-focused SPIRIT checks to observational or retrospective studies must be qualified.

## Limitations and reporting

This check used the evidence excerpts, guideline references, and the full available protocol PDFs without first reading the system-generated finding explanations, as prescribed in `eval/LABELING_GUIDE.md`. It was not an independent clinical expert review; public protocol PDFs may omit ethics submission attachments, and their absence does not establish an incomplete official submission. `partly` is not equivalent to a verified issue.
The full source of truth for every decision and comment is `eval/human_check/verified_findings_check.csv`; do not use this summary to overwrite blind labels or historical ablation outputs.
