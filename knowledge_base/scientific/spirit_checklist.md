# SPIRIT 2025 — Scientific Protocol Review Knowledge Base

**Authority:** Chan et al., JAMA 2025;334:435–443 (SPIRIT 2025, 34 principal items).
**Official table:** https://jamanetwork.com/journals/jama/fullarticle/2833408

This knowledge base covers every official SPIRIT 2025 checklist identifier including sub-items. Wording below paraphrases the published checklist; use the original guidance for final assessment. Applicable principally to randomized trials. **A completed checklist is evidence of reporting completeness, not proof of high-quality scientific design.**

## Core review rules
- Screen each item in the full PDF, tables, appendices, and referenced documents; do not judge solely by an exact heading.
- Separate *not located*, *ambiguous*, *not applicable* and *clearly documented*. Missing headings alone are not findings.
- For each suggested deficiency, cite a precise page and real quote; if genuinely missing from the complete document, flag for human review without fabricating a quotation.
- Inclusion and exclusion are independently checked under SPIRIT-14a.
- If applicability is unclear or the file is an abridged synopsis, report insufficient evidence rather than scoring every unseen item as missing.
- Keep the SPIRIT checklist dimension separate from independent medical/methodological quality judgement and ICH-GCP obligations.

## All 34 items and sub-items (2025)
- **SPIRIT-1a — Protocol title**: Specify trial design, participant population and intervention in the title.
- **SPIRIT-1b — Structured summary**: Provide a structured summary of trial design and methods.
- **SPIRIT-2 — Protocol version**: Identify protocol version and date.
- **SPIRIT-3a — Contributors**: Give contributor names, affiliations and roles.
- **SPIRIT-3b — Sponsor**: Give sponsor name and contact.
- **SPIRIT-3c — Sponsor influence**: Describe sponsor/funder responsibilities and authority.
- **SPIRIT-3d — Oversight roles**: Describe coordinating and oversight groups when relevant. (*Conditional; check relevance.*)
- **SPIRIT-4 — Registry**: Give registry, registration number, URL and registration date.
- **SPIRIT-5 — Protocol / SAP access**: State where protocol and statistical analysis plan are accessible.
- **SPIRIT-6 — Data sharing**: Explain access to de-identified data, code and related materials.
- **SPIRIT-7a — Funding**: Identify support and funding sources.
- **SPIRIT-7b — Conflicts**: Disclose relevant financial and nonfinancial conflicts.
- **SPIRIT-8 — Dissemination**: Describe dissemination to participants, professionals and public.
- **SPIRIT-9a — Background**: Give scientific rationale and existing benefits/harms evidence.
- **SPIRIT-9b — Comparator rationale**: Justify selected comparison condition. (*Conditional; check relevance.*)
- **SPIRIT-10 — Objectives**: State objectives regarding benefits and harms.
- **SPIRIT-11 — Patient and public involvement**: Describe involvement or plans in trial design, conduct or reporting.
- **SPIRIT-12 — Trial design**: Describe design, allocation ratio and trial framework.
- **SPIRIT-13 — Setting**: Give settings and locations of participating sites.
- **SPIRIT-14a — Participant eligibility**: Specify participant eligibility including inclusion and exclusion criteria.
- **SPIRIT-14b — Site/staff eligibility**: Where relevant, specify sites and intervention-provider eligibility. (*Conditional; check relevance.*)
- **SPIRIT-15a — Interventions**: Describe interventions/comparators sufficiently for replication.
- **SPIRIT-15b — Stopping or modifications**: State criteria for changing/discontinuing assigned treatments. (*Conditional; check relevance.*)
- **SPIRIT-15c — Adherence**: Describe adherence strategies and monitoring when relevant. (*Conditional; check relevance.*)
- **SPIRIT-15d — Concomitant care**: Specify allowed and disallowed concomitant care. (*Conditional; check relevance.*)
- **SPIRIT-16 — Outcomes**: Define primary and secondary outcomes with variable, metric, aggregation and time point.
- **SPIRIT-17 — Harms**: Describe harms definitions and ascertainment.
- **SPIRIT-18 — Timeline**: Specify schedule of enrolment, intervention, visits and measurements.
- **SPIRIT-19 — Sample size**: Report sample-size rationale and assumptions.
- **SPIRIT-20 — Recruitment**: Describe methods to reach planned sample.
- **SPIRIT-21a — Sequence generation**: State who generates random allocation and how.
- **SPIRIT-21b — Randomisation detail**: Describe type of randomisation and stratification; keep predictability-sensitive details restricted.
- **SPIRIT-22 — Concealment**: Describe allocation-concealment mechanism.
- **SPIRIT-23 — Assignment implementation**: Specify allocation-sequence access for enrolling and assigning staff.
- **SPIRIT-24a — Blinded parties**: State who is blinded or explicitly state an open-label design.
- **SPIRIT-24b — Masking implementation**: If blinded, describe how and intervention similarity. (*Conditional; check relevance.*)
- **SPIRIT-24c — Unblinding**: If blinded, describe permissible unblinding and procedure. (*Conditional; check relevance.*)
- **SPIRIT-25a — Data collection**: Describe measurements, instruments and data-quality safeguards.
- **SPIRIT-25b — Retention / follow-up**: Describe retention and follow-up for discontinuers/deviations.
- **SPIRIT-26 — Data management**: Describe data entry, coding, security, storage and quality controls.
- **SPIRIT-27a — Main analyses**: Specify comparisons of primary/secondary outcomes and harms.
- **SPIRIT-27b — Analysis populations**: Define analysis sets and treatment-group attribution.
- **SPIRIT-27c — Missing data**: Explain handling of missing data in analysis.
- **SPIRIT-27d — Additional analyses**: Describe any planned subgroup, sensitivity or other analyses. (*Conditional; check relevance.*)
- **SPIRIT-28a — DMC**: Describe DMC oversight or justify no DMC.
- **SPIRIT-28b — Interim/stopping**: Describe interim analyses, stopping and decision authority. (*Conditional; check relevance.*)
- **SPIRIT-29 — Trial monitoring**: Describe monitoring frequency/methods or explain absence.
- **SPIRIT-30 — Ethics review**: Describe ethics/IRB approval plans.
- **SPIRIT-31 — Amendments**: Describe communication of protocol changes.
- **SPIRIT-32a — Consent procedure**: Identify who obtains informed consent/assent and how.
- **SPIRIT-32b — Optional further use**: Specify additional consent for ancillary data/specimens when relevant. (*Conditional; check relevance.*)
- **SPIRIT-33 — Confidentiality**: Describe confidentiality protection throughout trial lifecycle.
- **SPIRIT-34 — Post-trial care**: Specify ancillary/posttrial care and compensation for trial injury as relevant.

## Legacy deterministic-check identifiers — compatibility ONLY
The existing deterministic checks in `src/protocol_review/tools/checks.py` emit the following **project-internal 2013-era meanings**. Do not cite these bare codes as official 2025 item references; translate or migrate in a separate verified change with test updates.
- `SPIRIT-02` (legacy check) → candidate SPIRIT 2025 item `4`; verify check semantics before migration.
- `SPIRIT-08` (legacy check) → candidate SPIRIT 2025 item `12`; verify check semantics before migration.
- `SPIRIT-10` (legacy check) → candidate SPIRIT 2025 item `14a`; verify check semantics before migration.
- `SPIRIT-12` (legacy check) → candidate SPIRIT 2025 item `16`; verify check semantics before migration.
- `SPIRIT-14` (legacy check) → candidate SPIRIT 2025 item `19`; verify check semantics before migration.
- `SPIRIT-16` (legacy check) → candidate SPIRIT 2025 item `21a/21b`; verify check semantics before migration.
- `SPIRIT-17` (legacy check) → candidate SPIRIT 2025 item `24a/24b`; verify check semantics before migration.
- `SPIRIT-20` (legacy check) → candidate SPIRIT 2025 item `27a`; verify check semantics before migration.
- `SPIRIT-21` (legacy check) → candidate SPIRIT 2025 item `28a`; verify check semantics before migration.
- `SPIRIT-22` (legacy check) → candidate SPIRIT 2025 item `28b`; verify check semantics before migration.

## Sources / limitations
- https://www.bmj.com/content/389/bmj-2024-081477
- https://jamanetwork.com/journals/jama/fullarticle/2833408
- No local SOP has been incorporated. SPIRIT is a reporting guideline, not an Israeli legal submission checklist.
