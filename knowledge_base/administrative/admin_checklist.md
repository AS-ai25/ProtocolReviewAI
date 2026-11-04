# Administrative submission checklist (Helsinki / IRB committee intake)

Reference checklist for the Administrative Review Agent. Codes are stable and are
cited in findings as `guideline_ref`. Any failed item makes the submission
administratively incomplete under the project decision rule: the coordinator returns
it to the submitter instead of forwarding it to scientific review. Items marked
**blocking** are the most serious. Applicability and evidence limitations are
defined in the protocol-only versus submission-package guidance below.

| Code | Requirement | Blocking |
|------|-------------|----------|
| ADMIN-CHK-01 | Title page with a descriptive, unambiguous protocol title | no |
| ADMIN-CHK-02 | Protocol version number AND version date on the title page (and ideally in the footer) | no (major) |
| ADMIN-CHK-03 | Trial registration identifier (ClinicalTrials.gov NCT number) cited; must resolve to an existing registry record | no (major) |
| ADMIN-CHK-04 | Principal Investigator named with affiliation | no (major) |
| ADMIN-CHK-05 | Sponsor (or "investigator-initiated") stated | no (major) |
| ADMIN-CHK-06 | Participant information sheet + informed consent form attached or referenced as an appendix | **yes** |
| ADMIN-CHK-07 | Insurance / indemnity / compensation-for-injury statement | **yes** |
| ADMIN-CHK-08 | Statement of compliance with the Declaration of Helsinki, ICH-GCP and local regulations; ethics approval section | no (major) |
| ADMIN-CHK-09 | PDF is text-based and complete (not scanned images, no missing pages, no truncated sections) | **yes** |
| ADMIN-CHK-10 | All standard protocol sections present: background, objectives, design, eligibility, interventions, outcomes, sample size, statistics, ethics, consent, safety, data management | missing core section = major |
| ADMIN-CHK-11 | Investigator signature page / CV referenced | no (minor) |
| ADMIN-CHK-12 | Contact details for the study team (email/telephone) | no (minor) |
| ADMIN-CHK-13 | Document internally consistent: title, version and trial ID identical on every page where they appear; table of contents matches headings | no (major) |
| ADMIN-CHK-14 | Language: protocol in English or Hebrew; consent form in the participants' language | no (major) |
| ADMIN-CHK-15 | Appendices listed in the protocol are actually included (questionnaires, case report forms, investigator brochure if drug study) | no (major) |

## Decision rule for the Administrative Review Agent

* `accepted = true` only when **every** item is satisfied. The administrative part must be
  100% complete: any failed item, including minor ones, is written to the report and the
  submission is returned to the submitter; scientific review does not start.
  "Blocking" items are the most serious ones, listed first in the report.
* Every finding must quote the page where the problem is visible, or state
  explicitly that the item is absent from the whole document (page 0).
* Do not re-report the deterministic rule findings you receive as input; add
  only context-dependent findings (e.g. an appendix referenced but missing,
  version mismatch between pages, consent form in the wrong language).


## Protocol-only versus submission-package review (applicability addendum, 2026-11-04)

**Scope and status.** This appendix is a source-attributed supplementary crosswalk, not an approved Sheba SOP or a legal approval rule. It supplements but DOES NOT renumber, reorder, or amend the original ADMIN-CHK-01..15 codes and their existing blocking values. Local protocol-format templates supplied by the research team are *practice examples*, not evidence of a binding national requirement. For binding local requirements, refer to the current Ministry of Health Procedure 14 and the institution's approved SOP.

**Two review objects must be distinguished.** (A) A stand-alone public protocol PDF is assessed for information *within the protocol*. (B) A complete Helsinki/IRB submission package can be checked for separately required attachments after the required document inventory and trial category are known. The absence of a consent form, insurance document, signed declaration, or investigator brochure from a public protocol PDF **does not establish** that it was absent from the actual submission. Such items are `NOT_ASSESSABLE_FROM_PROTOCOL`, not verified omissions; do not create MISSING_CONSENT_FORM, MISSING_INSURANCE or MISSING_DOCUMENT solely on this basis. An unmet condition in the *actual supplied submission package*, where that document is required, can be evaluated separately.

**Decision caution.** The project's current 100% administrative intake gate remains unchanged as code behavior, but interpreting RETURNED_ADMIN for a stand-alone public protocol must reflect the limited input, not a factual claim of IRB noncompliance. Preserve baseline and force_scientific evaluation settings; do not revise existing gold labels retroactively.

### Additional protocol-content review guidance mapped to existing codes

| Existing code | Protocol-only review question | Applicability / evidence caveat |
|---|---|---|
| ADMIN-CHK-01 | Is the title on the protocol title page clear, and internally consistent with the synopsis? | Different short title is not automatically an error; assess substantive discrepancy. |
| ADMIN-CHK-02 | Are the protocol version and date identifiable? | An amendment might show multiple historical dates; examine what is labeled current. |
| ADMIN-CHK-03 | Is a registry ID provided when applicable to the trial design and version? | A missing NCT does not by itself prove an unregistered observational study or retrospectively authored pre-registration version. |
| ADMIN-CHK-04 | Are PI and responsible study personnel identified? | Distinguish global PI from site PI. |
| ADMIN-CHK-05 | Is the sponsor/initiator identifiable? | Investigator-initiated studies need not have a commercial sponsor. |
| ADMIN-CHK-09 | Is the PDF readable and complete enough for review? | A short public synopsis is insufficient evidence that unshown sections do not exist in the complete protocol. |
| ADMIN-CHK-10 | Are protocol sections identifiable: background/rationale, objectives/hypotheses, design, participant selection, recruitment, interventions or exposures, visits/follow-up, outcomes, sample size or its context-appropriate rationale, analysis, data governance, ethics, safety if applicable? | Check substantive content across the document, not just section names; scientific adequacy is assessed by the scientific agent. |
| ADMIN-CHK-13 | Are title, protocol ID, version/date and numeric details internally consistent where repeated? | Evaluate amendments, local versus global enrollment and differing analysis populations before reporting contradiction. |
| ADMIN-CHK-14 | Is the document language reviewable and consent language addressed when applicable? | The participant's actual consent language cannot be confirmed without the consent materials. |
| ADMIN-CHK-15 | Are specifically referenced appendices present in the *material provided*? | Mark any absent appendix as 'not supplied for this review'; distinguish this from a proven incomplete application package. |

### Protocol-format examples supplied by a local research team

The following are helpful preparation templates, **not** independent legal obligations and not new checklist IDs:

- **Medical research request / synopsis:** title, version/date, PI, short background, objective/rationale, recruitment, sequence of clinical versus research procedures and post-treatment follow-up, local-site enrollment (separate from total multicentre enrollment), ages and sex, main inclusion/exclusion/withdrawal criteria, study duration, and safeguards for pregnancy, minors or reduced decision-making capacity where relevant.
- **Interventional protocol:** dated/versioned title page; sponsor and signatory details; literature review and rationale; objectives and defined endpoints; enrollment/site counts; recruitment/consent; eligibility/withdrawal; study schedule; reproducible interventions and follow-up; specimen handling (if applicable); privacy and data retention; analysis; foreseeable risks and ethical considerations; references/appendices.
- **Existing-data, retrospective or questionnaire protocol:** sponsor and signed document metadata where required by local policy; rationale, objectives and measurable outcomes; cohort/data sources, recruitment/consent or documented waiver pathway; eligibility and dates; extraction and analysis plan; data minimization, transfer, access control, linkage, retention, destruction and institutional responsibilities. Do not demand randomization or drug product details where inapplicable.

**Source hierarchy:** official Ministry of Health Procedure 14 and current hospital SOP (highest for Israeli submission requirements); official SPIRIT 2025 and ICH E6(R3)/E8(R1) for their respective trial scopes; Declaration of Helsinki 2024 for ethics; Soroka forms page as an institutional example; CASRAI pathway as secondary orientation only. A locally supplied preparation template is not a signed Sheba SOP.

**Sources:**
- Israeli Ministry of Health, Procedure 14 (official current version): https://www.gov.il/he/collectors/policies/?UnitId=6b83f07d-a237-4397-8ed4-e771ffce18ed&officeId=104cb0f4-d65a-4692-b590-94af928c19c0
- Procedure 14 text and submission package breakdown (reproduced Ministry circular, secondary host): https://www.wikirefua.org.il/w/index.php?title=ניסויים_רפואיים_בבני_אדם
- Soroka Helsinki procedures/forms (institution-specific example; site content not independently retrievable here): https://hospitals.clalit.co.il/soroka/he/ac-se/helsinki/Pages/procedures-and-forms.aspx
- Declaration of Helsinki (2024): https://www.wma.net/policies-post/wma-declaration-of-helsinki/
- CASRAI clinical trials pathway (secondary): https://casrai.org/guides/israel-clinical-trials-helsinki-committee-pathway
