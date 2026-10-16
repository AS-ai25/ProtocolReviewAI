# Administrative submission checklist (Helsinki / IRB committee intake)

Working copy for the Administrative Review Agent. Codes are stable and are
cited in findings as `guideline_ref`. Items marked **blocking** make the
submission administratively incomplete: the coordinator returns it to the
submitter instead of forwarding it to scientific review.

> Status: draft compiled by the team from common Israeli Helsinki committee and
> IRB intake requirements. Ron to verify against the committee's official SOP
> before Checkpoint 2.

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

* `accepted = true` when no **blocking** item fails. Major/minor failures are
  reported but do not stop scientific review.
* Every finding must quote the page where the problem is visible, or state
  explicitly that the item is absent from the whole document (page 0).
* Do not re-report the deterministic rule findings you receive as input; add
  only context-dependent findings (e.g. an appendix referenced but missing,
  version mismatch between pages, consent form in the wrong language).
