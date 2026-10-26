# Israel Clinical Trial Protocol Candidate Dataset (17 studies)

**Project:** BIU DS23 – Multi-Agent Clinical Trial Protocol Review System  
**Team:** Ron Levi and Amir Shmaryahu  
**Updated:** 2026-10-21  
**Dataset status:** Candidate discovery list; **not** a verified or labeled evaluation dataset.

## Purpose
This directory consolidates **17 distinct NCT study records** associated in earlier research with clinical sites in Israel. It includes **the original 11 records supplied in `protocol_sources.csv`**, unchanged in their original eight fields, plus **six additional candidates**. Active trial status is **not required** for inclusion in this candidate inventory. The emphasis is on finding potentially usable, publicly accessible **protocol PDFs** for scientific review.

## Contents
- `protocol_sources_17.csv` — master source table (17 rows; NCT, study, Israeli site, public PDF link, source record, and verification workflow fields).
- `README.md` — methods, limitations, and workflow.
- `protocol_download_checklist.md` — practical checklist to validate each PDF before use.

**Important:** This package contains **links and metadata, not downloaded protocol PDFs**. The original 11 links were provided by the user; six further links were collected in the preceding conversation. The URLs have **not** been re-opened or downloaded in this package. An accessible URL is not evidence that a file is a complete protocol or that reuse/redistribution is authorized.

## Inclusion criteria for the candidate list
1. An NCT identifier was associated with the study.
2. An Israeli institution was reported as an investigator/site/participating center in previous findings. This still requires per-record verification in the current study record and the document itself.
3. A direct URL with a `Prot_` or `Prot_SAP_` filename was previously identified.

**Not guaranteed:** recruiting/active status, ongoing Israeli-site participation, completeness of the PDF, original protocol language, file accessibility, rights to upload to GitHub, rights to transmit to an external LLM, or scientific suitability.

## CSV fields
- `NCT_ID`: study registration ID.
- `Study`, `Israeli_center`: candidate study title and reported center(s).
- `Protocol_version_or_date`: preliminary date/version info, not always verified.
- `Notes`: cautions and previously collected observations.
- `Public_PDF_URL`: direct candidate PDF link.
- `Evidence_level`: earlier preliminary assessment (not an externally audited confidence score).
- `Current_status_confirmed`: all `NO` until independently verified. In this collection, **the study may be completed**; this is acceptable for scientific protocol review.
- `Document_type_in_link`: filename-based classification (`Prot` or `Prot_SAP`), **not a determination of complete contents**.
- `PDF_downloaded`, `PDF_opened_and_checked`, `Public_use_permissions_checked`: operational checklist flags; default `NO`.
- `Label_status`: default `NOT_STARTED`.
- `Dataset_split`: default `UNASSIGNED`; decide before label-aware model development to prevent leakage.
- `Source_record_URL`: ClinicalTrials.gov record URL for cross-checking study and site metadata.

## How to build a defensible evaluation set
1. **Verify document:** Open each PDF, make sure it is the complete study protocol (not only a synopsis, SAP, ICF, registry listing, or outdated amendment), and record protocol version/date and page count. Mark `PDF_opened_and_checked=YES` only after inspection.
2. **Verify Israel-site association:** Check the ClinicalTrials.gov record (Locations / Contacts), protocol cover/site appendix and date of participation. Search variants such as `Sheba`, `Chaim Sheba`, `Tel Hashomer`, `Ramat Gan`, local postcode, `Sourasky`, `Hadassah`, `Rambam` etc. Do not infer sites from PI affiliation alone.
3. **Check rights and confidentiality:** Some public PDFs include `confidential` or proprietary notices. Public accessibility does **not** automatically grant redistribution, GitHub hosting, or AI-provider upload. Seek appropriate permission or retain only links and locally permitted copies.
4. **Freeze dataset split:** Separate `development` from `evaluation` before examining model outputs. Keep the evaluation set blind; avoid duplicate protocols or revised versions in both splits.
5. **Blind annotation:** Have clinical professionals label genuine findings without access to system outputs. Record category, domain, page, quote, guideline reference, severity and reviewer identity/date in the agreed JSON schema. Agree adjudication procedure for disagreements.
6. **Run four-way ablation fairly:** Single agent; single agent with the same deterministic verification; multi-agent without critic; full multi-agent. Same documents, same matching rule, same model/settings where relevant. Report precision of verified findings, recall, unverified count, tokens and runtime.
7. **Human validity check:** Manually inspect 30 sampled verified findings for whether evidence supports each finding. Report failures explicitly.

## Administrative vs scientific checks
ClinicalTrials.gov public protocols often lack consent/insurance submission packets needed by the administrative gate. For this dataset, use the **evaluation-only** `force_scientific` mode to run the scientific stage even when `RETURNED_ADMIN` applies; never treat bypass as production behavior. The administrative gate should be evaluated separately on suitable synthetic or authorized submission packages.

## Prioritization
Start with several PDFs verified as full protocols, not necessarily recent or active. A smaller credible, blindly labeled real-protocol set is better than an inflated count. The Charter v1.4 envisages 10–15 development/evaluation candidates and a reduced-scope fallback of five if necessary.

## Data provenance and cautions
- 11 baseline records: the user's uploaded `protocol_sources.csv`.
- Six additions: prior conversation findings (NCT04084990, NCT04202887, NCT04523324, NCT04179786, NCT03504189, NCT04348656).
- All 17 URLs are **candidate links**, not independently verified downloads in this delivery.
- Do not claim that 17 complete, presently active, reusable protocols have been obtained. Do not publish internal hospital records or identifiable patient information.
