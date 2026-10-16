# SPIRIT checklist - condensed working copy

Items a clinical trial protocol must address. Codes `SPIRIT-nn` follow the
SPIRIT 2013 numbering, which the team uses as the stable reference; SPIRIT 2025
(BMJ 2025) keeps the same content areas with some renumbering and additions
(open science, patient involvement, harms). **Ron to replace this file with the
verified SPIRIT 2025 item list before Checkpoint 2.**

## Administrative information
- SPIRIT-01 Title: descriptive, identifies design, population, interventions, acronym.
- SPIRIT-02 Trial registration: registry name and identifier; registry data set consistent with the protocol (enrollment, phase, outcomes, interventions).
- SPIRIT-03 Protocol version: identifier and date.
- SPIRIT-04 Funding: sources and types of financial, material and other support.
- SPIRIT-05 Roles and responsibilities: names, affiliations and roles of contributors; sponsor contact; sponsor/funder role in design, data, analysis, publication; coordinating centre, steering committee, endpoint adjudication, data management team.

## Introduction
- SPIRIT-06 Background and rationale: scientific background, relevant studies (published and unpublished), justification for the trial, explanation for choice of comparators.
- SPIRIT-07 Objectives: specific objectives or hypotheses.
- SPIRIT-08 Trial design: type (parallel, crossover, factorial, single group), allocation ratio, framework (superiority, equivalence, non-inferiority, exploratory).

## Methods: participants, interventions, outcomes
- SPIRIT-09 Study setting: countries, type of sites, list of sites.
- SPIRIT-10 Eligibility criteria: inclusion and exclusion criteria for participants (age range, diagnosis, etc.) and, if applicable, for sites and investigators; criteria must be identical wherever they are repeated.
- SPIRIT-11 Interventions: each arm with sufficient detail for replication; criteria for discontinuing or modifying interventions; adherence strategies; permitted/prohibited concomitant care.
- SPIRIT-12 Outcomes: primary, secondary and other outcomes with the specific measurement variable, analysis metric, method of aggregation and time point; rationale for the primary outcome.
- SPIRIT-13 Participant timeline: schedule of enrolment, interventions, assessments and visits (schematic diagram recommended).
- SPIRIT-14 Sample size: estimated number of participants needed with the clinical and statistical assumptions supporting the calculation (effect size, variability, alpha, power, dropout). The number must be stated once and used consistently throughout the protocol.
- SPIRIT-15 Recruitment: strategies to achieve adequate enrolment.

## Methods: assignment of interventions (for controlled trials)
- SPIRIT-16a Sequence generation: method (e.g. computer-generated random numbers), stratification factors, block size (kept hidden).
- SPIRIT-16b Allocation concealment mechanism (central telephone/web randomisation, sequentially numbered opaque sealed envelopes).
- SPIRIT-16c Implementation: who generates the sequence, who enrols, who assigns.
- SPIRIT-17a Blinding (masking): who is blinded (participants, care providers, outcome assessors, analysts) and how; or explicit open-label statement.
- SPIRIT-17b Circumstances and procedure for unblinding.

## Methods: data collection, management, analysis
- SPIRIT-18a Data collection methods: plans for assessment and collection of outcome, baseline and other data; data quality (training, duplicate measurements); reference to data collection forms.
- SPIRIT-18b Retention and follow-up: plans to promote retention and complete follow-up, including data to be collected for participants who discontinue.
- SPIRIT-19 Data management: entry, coding, security, storage, range checks.
- SPIRIT-20a Statistical methods for primary and secondary outcomes; reference to the statistical analysis plan.
- SPIRIT-20b Methods for additional analyses (subgroup, adjusted).
- SPIRIT-20c Analysis population definition (ITT, per-protocol) and handling of missing data.

## Methods: monitoring
- SPIRIT-21a Data monitoring committee: composition, role, independence; or explanation of why none is needed; interim analyses and stopping guidelines.
- SPIRIT-21b Interim analyses and stopping guidelines, who decides to terminate the trial.
- SPIRIT-22 Harms: plans for collecting, assessing, reporting and managing solicited and spontaneously reported adverse events.
- SPIRIT-23 Auditing: frequency and procedures, independence from investigators and sponsor.

## Ethics and dissemination
- SPIRIT-24 Research ethics approval: plans for seeking REC/IRB approval.
- SPIRIT-25 Protocol amendments: communication of modifications to relevant parties.
- SPIRIT-26a Consent: who obtains consent and how.
- SPIRIT-26b Additional consent for ancillary studies / biological specimens.
- SPIRIT-27 Confidentiality: how personal information is collected, shared and maintained.
- SPIRIT-28 Declaration of interests: financial and other competing interests.
- SPIRIT-29 Access to data: who will have access to the final dataset.
- SPIRIT-30 Ancillary and post-trial care; compensation for trial-related harm.
- SPIRIT-31a Dissemination policy: results communication to participants, professionals, public; publication restrictions.
- SPIRIT-31b Authorship eligibility guidelines.
- SPIRIT-31c Plans for public access to protocol, dataset, statistical code.
- SPIRIT-32 Informed consent materials: model consent form provided as appendix.
- SPIRIT-33 Biological specimens: collection, evaluation, storage for future use.

## How the Scientific Review Agent uses this list
* Findings cite the item code (`SPIRIT-14`) in `guideline_ref`.
* Severity guidance: missing primary outcome, unjustified sample size, undisclosed
  randomisation in a randomised trial, contradictory eligibility criteria or a
  protocol/registry contradiction are **major** or **critical**; missing minor
  items (authorship, data access) are **minor**.
* Internal contradictions (numbers, dates, criteria differing between sections)
  are a distinct category `INTERNAL_CONTRADICTION` and must quote BOTH places.
