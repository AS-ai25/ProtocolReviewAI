# SPIRIT 2025 - Scientific Protocol Review Knowledge Base

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
- **SPIRIT-1a - Protocol title**: Specify trial design, participant population and intervention in the title.
- **SPIRIT-1b - Structured summary**: Provide a structured summary of trial design and methods.
- **SPIRIT-2 - Protocol version**: Identify protocol version and date.
- **SPIRIT-3a - Contributors**: Give contributor names, affiliations and roles.
- **SPIRIT-3b - Sponsor**: Give sponsor name and contact.
- **SPIRIT-3c - Sponsor influence**: Describe sponsor/funder responsibilities and authority.
- **SPIRIT-3d - Oversight roles**: Describe coordinating and oversight groups when relevant. (*Conditional; check relevance.*)
- **SPIRIT-4 - Registry**: Give registry, registration number, URL and registration date.
- **SPIRIT-5 - Protocol / SAP access**: State where protocol and statistical analysis plan are accessible.
- **SPIRIT-6 - Data sharing**: Explain access to de-identified data, code and related materials.
- **SPIRIT-7a - Funding**: Identify support and funding sources.
- **SPIRIT-7b - Conflicts**: Disclose relevant financial and nonfinancial conflicts.
- **SPIRIT-8 - Dissemination**: Describe dissemination to participants, professionals and public.
- **SPIRIT-9a - Background**: Give scientific rationale and existing benefits/harms evidence.
- **SPIRIT-9b - Comparator rationale**: Justify selected comparison condition. (*Conditional; check relevance.*)
- **SPIRIT-10 - Objectives**: State objectives regarding benefits and harms.
- **SPIRIT-11 - Patient and public involvement**: Describe involvement or plans in trial design, conduct or reporting.
- **SPIRIT-12 - Trial design**: Describe design, allocation ratio and trial framework.
- **SPIRIT-13 - Setting**: Give settings and locations of participating sites.
- **SPIRIT-14a - Participant eligibility**: Specify participant eligibility including inclusion and exclusion criteria.
- **SPIRIT-14b - Site/staff eligibility**: Where relevant, specify sites and intervention-provider eligibility. (*Conditional; check relevance.*)
- **SPIRIT-15a - Interventions**: Describe interventions/comparators sufficiently for replication.
- **SPIRIT-15b - Stopping or modifications**: State criteria for changing/discontinuing assigned treatments. (*Conditional; check relevance.*)
- **SPIRIT-15c - Adherence**: Describe adherence strategies and monitoring when relevant. (*Conditional; check relevance.*)
- **SPIRIT-15d - Concomitant care**: Specify allowed and disallowed concomitant care. (*Conditional; check relevance.*)
- **SPIRIT-16 - Outcomes**: Define primary and secondary outcomes with variable, metric, aggregation and time point.
- **SPIRIT-17 - Harms**: Describe harms definitions and ascertainment.
- **SPIRIT-18 - Timeline**: Specify schedule of enrolment, intervention, visits and measurements.
- **SPIRIT-19 - Sample size**: Report sample-size rationale and assumptions.
- **SPIRIT-20 - Recruitment**: Describe methods to reach planned sample.
- **SPIRIT-21a - Sequence generation**: State who generates random allocation and how.
- **SPIRIT-21b - Randomisation detail**: Describe type of randomisation and stratification; keep predictability-sensitive details restricted.
- **SPIRIT-22 - Concealment**: Describe allocation-concealment mechanism.
- **SPIRIT-23 - Assignment implementation**: Specify allocation-sequence access for enrolling and assigning staff.
- **SPIRIT-24a - Blinded parties**: State who is blinded or explicitly state an open-label design.
- **SPIRIT-24b - Masking implementation**: If blinded, describe how and intervention similarity. (*Conditional; check relevance.*)
- **SPIRIT-24c - Unblinding**: If blinded, describe permissible unblinding and procedure. (*Conditional; check relevance.*)
- **SPIRIT-25a - Data collection**: Describe measurements, instruments and data-quality safeguards.
- **SPIRIT-25b - Retention / follow-up**: Describe retention and follow-up for discontinuers/deviations.
- **SPIRIT-26 - Data management**: Describe data entry, coding, security, storage and quality controls.
- **SPIRIT-27a - Main analyses**: Specify comparisons of primary/secondary outcomes and harms.
- **SPIRIT-27b - Analysis populations**: Define analysis sets and treatment-group attribution.
- **SPIRIT-27c - Missing data**: Explain handling of missing data in analysis.
- **SPIRIT-27d - Additional analyses**: Describe any planned subgroup, sensitivity or other analyses. (*Conditional; check relevance.*)
- **SPIRIT-28a - DMC**: Describe DMC oversight or justify no DMC.
- **SPIRIT-28b - Interim/stopping**: Describe interim analyses, stopping and decision authority. (*Conditional; check relevance.*)
- **SPIRIT-29 - Trial monitoring**: Describe monitoring frequency/methods or explain absence.
- **SPIRIT-30 - Ethics review**: Describe ethics/IRB approval plans.
- **SPIRIT-31 - Amendments**: Describe communication of protocol changes.
- **SPIRIT-32a - Consent procedure**: Identify who obtains informed consent/assent and how.
- **SPIRIT-32b - Optional further use**: Specify additional consent for ancillary data/specimens when relevant. (*Conditional; check relevance.*)
- **SPIRIT-33 - Confidentiality**: Describe confidentiality protection throughout trial lifecycle.
- **SPIRIT-34 - Post-trial care**: Specify ancillary/posttrial care and compensation for trial injury as relevant.

## Legacy deterministic-check identifiers - compatibility ONLY
The deterministic checks in `src/protocol_review/tools/checks.py` use legacy project-internal code meanings. These must not be interpreted as official SPIRIT 2025 item numbers. No automatic correspondence between legacy checks and the official 2025 checklist is asserted here. The official 2025 item list above remains the reference for scientific review.

## Sources / limitations
- https://www.bmj.com/content/389/bmj-2024-081477
- https://jamanetwork.com/journals/jama/fullarticle/2833408
- No local SOP has been incorporated. SPIRIT is a reporting guideline, not an Israeli legal submission checklist.


## Israeli protocol-format and study-type applicability addendum (2026-11-04)

**Compatibility guarantee:** The full 34-item list and every existing SPIRIT-2025 identifier above remain unchanged, in the original order. This material is supplementary interpretive guidance only. No new codes are introduced and no historical manual label is edited or re-scored.

### Protocol sections commonly requested in local preparation templates

The research-team-provided Hebrew format examples describe a medical-research synopsis (title/version/date/PI, brief background and rationale, objectives, recruitment, local enrollment, age and sex, inclusion/exclusion/withdrawal, visit and clinical follow-up schedule, pregnancy/minors/incapacity safeguards) and the full protocol (literature and bibliography, hypotheses, product/intervention if any, study arms, clinical vs research-only procedures, analyses, confidentiality, data retention, samples, risks and ethics). These are *examples of expected detail*, not a verified mandatory Sheba/Ministry template.

| Existing SPIRIT 2025 item(s) | Supplemental question for a randomized trial | Applicability guardrail |
|---|---|---|
| SPIRIT-1a, SPIRIT-2, SPIRIT-3a-3d | Can the reviewer identify title, dated version, responsible people, sponsor and oversight? | Do not equate missing site-level detail in a global protocol with absent local submission. |
| SPIRIT-9a, SPIRIT-9b, SPIRIT-10 | Do literature, rationale, comparator justification and objectives coherently support the trial? | Inference about clinical adequacy requires expert review. |
| SPIRIT-12, SPIRIT-13 | Are arms, allocation framework, participating settings and local-vs-global enrollment understandable? | No randomization requirements for observational studies. |
| SPIRIT-14a, SPIRIT-14b | Are inclusion, exclusion and site/staff eligibility described, including vulnerable groups where relevant? | Do not impose a universal exclusion of pregnant people, minors or people lacking capacity. Review protections and consent instead. |
| SPIRIT-15a-15d, SPIRIT-18 | Are intervention, concomitant care, participant timeline, visits, research-only vs routine-care activities, treatment termination and follow-up distinguishable? | Product details only if an investigational product is actually used. |
| SPIRIT-16, SPIRIT-19, SPIRIT-27a-27d | Are outcomes, measurements, sample-size rationale and statistical analysis linked and coherent? | Observational and exploratory designs may have different sample-size rationale. |
| SPIRIT-17, SPIRIT-28a-28b, SPIRIT-29 | Are harms, safety surveillance and stopping/monitoring responsibilities proportionate to risks? | Absence of a DMC is not a violation when justified. |
| SPIRIT-25a, SPIRIT-26, SPIRIT-33 | Are source data, access rights, coded identifier linkage, transfers (including cloud/cross-border), security, retention and disposal described? | Missing operational specifics may warrant clarification; do not prescribe a specific vendor or storage duration absent applicable policy. |
| SPIRIT-30, SPIRIT-31, SPIRIT-32a-32b, SPIRIT-34 | Are ethics review, amendments, consent/assent or justified waiver pathway, secondary reuse and posttrial provisions addressed where relevant? | Distinguish protocol statement from documentary proof of local approval or signed consent. |

### Other study designs, without misapplying SPIRIT

- **Observational cohort/case-control/cross-sectional, existing records and questionnaires:** use the relevant STROBE reporting framework as supplemental orientation, with protocol-specific questions about design, sources, eligibility, timeframe, confounding, missingness and consent/waiver. STROBE is primarily a reporting guideline for observational studies; it is not a regulatory protocol checklist. SPIRIT-21a to SPIRIT-24c randomization/blinding items are **not applicable** to a nonrandomized observational design.
- **Predictive modelling / AI (including pathology-based models):** where applicable, consult TRIPOD+AI or other model-specific guidance on target, predictors, training/test separation at patient level, external validation, performance and bias. Do not claim an experimental allocation was required.
- **Questionnaires / existing data:** clarify which records/variables are used, the period of collection, whether new patient contact occurs, who extracts identified data, how questionnaires are distributed and where information is transferred. Consent requirements depend on design and approved waiver pathways, not a blanket rule.

### Confidentiality and identifier-linkage distinction

**Pseudonymized / coded is not anonymous.** If a study retains a key linking participant codes to identities, it remains re-identifiable (coded/pseudonymized) data, even when the analytical dataset has direct identifiers removed. The example text supplied by the research team describes a linkage list retained on a password-protected hospital computer. Do not rewrite that as 'fully anonymous'; ask who controls the key, access permissions, separation, transfer safeguards, retention period and destruction/reuse policy. A password is one control, not a complete data protection plan. Hospital staff must access records under appropriate authorization; do not assume the PI is always the sole lawful extractor.

### Source precedence and reliability

- SPIRIT 2025 official statement: https://www.bmj.com/content/389/bmj-2024-081477
- ICH E6(R3) Principles/Annex 1: https://www.ema.europa.eu/en/scientific-guidelines/ich-e6-good-clinical-practice
- ICH E8(R1): https://www.ema.europa.eu/en/scientific-guidelines/ich-e8-general-considerations-clinical-studies
- WMA Helsinki 2024: https://www.wma.net/policies-post/wma-declaration-of-helsinki/
- STROBE: https://equator-network.org/reporting-guidelines/strobe/
- Israeli local SOP must be independently confirmed; a protocol template does not create a mandatory SPIRIT item.
