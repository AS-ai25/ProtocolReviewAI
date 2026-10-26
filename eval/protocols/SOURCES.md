# Protocol sources - real-protocol test set

See eval/LABELING_GUIDE.md section 1. Candidate list collected by Ron Levi (`protocol_sources.csv`,
`README_ron.md`, 2026-10-21); files received 2026-10-26 and checked by Amir.

**Provenance.** All 17 PDFs are the public "Study Documents" attached to the ClinicalTrials.gov record
(`cdn.clinicaltrials.gov/large-docs/...`). Each file received was compared with the CDN copy on
2026-10-26 (HTTP 200, identical byte size for all 17). `python eval/protocols/fetch_protocols.py`
re-downloads the set; the PDFs themselves are not committed (see "Licence / terms").

**Licence / terms.** The documents are published by the registry under the sponsor's upload (FDAAA 801 /
voluntary posting) and can be read and processed freely. 15 of 17 nevertheless carry a sponsor
"confidential" header, so the repository stores links + this table, not the files, and the evaluation
reports quote at most short passages (page + quote in the label files and the 30-finding check).
Nothing here comes from a hospital's internal records; the Sheba internal protocols and committee
comments discussed on 2026-10-21 are **not** part of this set.

**Gate check.** `eval/protocols/GATE_CHECK.md` (from `eval/gate_check.py`): the administrative gate
returns 16/17 - public protocols are not submission packages - which is why the ablation runs with
`force_scientific`.

**Split (proposed by Amir, to be confirmed by Ron before labeling starts).** 3 development protocols
for prompt / rule tuning, 14 evaluation protocols never used for tuning. The three documents under
10 pages are synopsis-level protocols; whether they stay in the evaluation set is the labeler's call -
dropping them leaves 11 evaluation protocols, within the charter's 10-15.

| case_id | NCT id | Title (short) | Source URL | Document version / date | Pages | Licence / terms checked | Dev or Eval |
|---|---|---|---|---|---|---|---|
| nct03390257 | NCT03390257 | Sinusway sinus-balloon device (3NT Medical) | https://clinicaltrials.gov/study/NCT03390257 | no version id; 3 Jul 2017 | 29 | yes (public CT.gov, confidential header) | eval |
| nct03503812 | NCT03503812 | MEDEA (LIFE+ Mediterranean diet, asthma) | https://clinicaltrials.gov/study/NCT03503812 | v1.0, Apr 2018 | 26 | yes (public CT.gov, confidential header) | dev |
| nct03504189 | NCT03504189 | PregSense non-invasive prenatal monitoring | https://clinicaltrials.gov/study/NCT03504189 | 5 May 2018 | 42 | yes (public CT.gov, confidential header) | eval |
| nct04002830 | NCT04002830 | Taliglucerase alfa, Gaucher type 3 | https://clinicaltrials.gov/study/NCT04002830 | v5.0, 10 Dec 2021 (Prot + SAP) | 55 | yes (public CT.gov, confidential header) | eval |
| nct04084990 | NCT04084990 | SAFER: sleep apnea and fetal growth restriction | https://clinicaltrials.gov/study/NCT04084990 | version date 21 Jul 2021 (Prot + SAP) | 19 | yes (public CT.gov, PI IP notice) | eval |
| nct04179786 | NCT04179786 | Sci-B-Vac hepatitis B vaccine, healthy volunteers | https://clinicaltrials.gov/study/NCT04179786 | v1.0, 4 Mar 2015 | 95 | yes (public CT.gov, confidential header) | eval |
| nct04186247 | NCT04186247 | PAZAZ: azithromycin/metronidazole in Crohn's | https://clinicaltrials.gov/study/NCT04186247 | v1.9, 12 Oct 2021 (Prot + SAP) | 56 | yes (public CT.gov, confidential header) | eval |
| nct04202887 | NCT04202887 | Epidural fentanyl dose and gastric emptying in labour | https://clinicaltrials.gov/study/NCT04202887 | 23 Sep 2019 (synopsis-level) | 4 | yes (public CT.gov) | eval (keep or drop: labeler's call) |
| nct04348656 | NCT04348656 | CONCOR-1 convalescent plasma, COVID-19 | https://clinicaltrials.gov/study/NCT04348656 | v8.0, 15 Jan 2021 | 78 | yes (public CT.gov, confidential header) | eval |
| nct04523324 | NCT04523324 | RIV4 vs IIV4 influenza vaccines, Israeli healthcare workers | https://clinicaltrials.gov/study/NCT04523324 | v3, 8 Dec 2019 (Prot + SAP) | 30 | yes (public CT.gov, confidential header) | dev |
| nct05199324 | NCT05199324 | INVEST master protocol | https://clinicaltrials.gov/study/NCT05199324 | v10.0, 9 Sep 2024 | 34 | yes (public CT.gov, confidential header) | eval |
| nct05796557 | NCT05796557 | ECSTATIC paediatric ECMO | https://clinicaltrials.gov/study/NCT05796557 | v1.4, 22 Apr 2024 (Prot + SAP) | 95 | yes (public CT.gov, confidential header) | eval |
| nct06846736 | NCT06846736 | ALK digital pathology outcome prediction (Sheba, retrospective) | https://clinicaltrials.gov/study/NCT06846736 | 30 Sep 2024 (synopsis-level) | 6 | yes (public CT.gov, confidential header) | eval (keep or drop: labeler's call) |
| nct07095049 | NCT07095049 | Apo-Si-K170A-C76 phase 1 (Interna Therapeutics, Hadassah) | https://clinicaltrials.gov/study/NCT07095049 | v4.0, 2024 | 81 | yes (public CT.gov, confidential header) | eval |
| nct07183462 | NCT07183462 | ALPRO: azithromycin and ampicillin for late PPROM (Sheba) | https://clinicaltrials.gov/study/NCT07183462 | 1 Jun 2025 | 12 | yes (public CT.gov, confidential header) | dev |
| nct07199218 | NCT07199218 | Terpene-enriched cannabis in ASD (Shaare Zedek) | https://clinicaltrials.gov/study/NCT07199218 | v3.0, 1 Sep 2025 | 47 | yes (public CT.gov, confidential header) | eval |
| nct07328308 | NCT07328308 | Delayed surveillance colonoscopy after piecemeal EMR (Rambam) | https://clinicaltrials.gov/study/NCT07328308 | 17 Dec 2025 (synopsis-level) | 9 | yes (public CT.gov) | eval (keep or drop: labeler's call) |

Version / date = what is printed on the document (parser + manual check of the first pages). Registry
status, phase and enrollment per protocol are in `GATE_CHECK.md`.
