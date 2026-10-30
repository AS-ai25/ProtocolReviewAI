> **SPIRIT 2025 migration:** New human labels must cite 2025 identifiers. Existing synthetic labels retain their historical version and must be migrated before pooling scores. Do not change blinded labels after viewing model output.

# Labeling guide for the real-protocol test set (owner: Ron)

Everything the evaluation needs from the data side, in the exact formats the scripts read.
Four deliverables, all committed to the official repository by **30 October 2026**:

1. the protocol PDFs + a source table,
2. one **blind** label file per protocol,
3. the knowledge base verified against SPIRIT 2025 and the committee SOP,
4. the 30-finding human check (after the ablation has run).

Rule zero: **label before you run**. Never open `outputs/`, `reports/results.md` or any system
finding for a protocol before its label file is committed. The evaluation is only credible if the
labels could not have been influenced by the system.

---

## 1. Protocols and source table

**Where to find them.** ClinicalTrials.gov attaches the protocol PDF (often together with the
statistical analysis plan) to some completed studies: open the study page → "Study Documents"
(API: `documentSection.largeDocumentModule.largeDocs`). Fallback: PubMed Central articles whose
supplementary material is the full protocol.

**Selection.** 10 to 15 protocols, English, text-based PDF (not scanned), ideally 20-80 pages,
mixed phases and sponsors. Include at least two with a known inconsistency if you can find them
(e.g. an amendment changed the sample size). Keep 2-3 aside as a development set; the rest is the
evaluation set and is never used for prompt tuning.

**Files.** `eval/protocols/<case_id>.pdf` with `case_id` = lower-case NCT id or a short slug,
e.g. `nct04470427.pdf`.

**Source table.** `eval/protocols/SOURCES.md`:

| case_id | NCT id | Title (short) | Source URL | Document version / date | Pages | Licence / terms checked | Dev or Eval |
|---|---|---|---|---|---|---|---|
| nct04470427 | NCT04470427 | mRNA-1273 COVE | https://clinicaltrials.gov/study/NCT04470427 | Protocol v6.0, 23 Dec 2020 | 141 | yes (public, CT.gov) | eval |

---

## 2. Blind label file (one per protocol)

Path: `eval/labeled_cases/<case_id>.json`. Copy `eval/labeled_cases/_TEMPLATE.json`.

```json
{
  "case_id": "nct04470427",
  "pdf": "eval/protocols/nct04470427.pdf",
  "nct_id": "NCT04470427",
  "labeler": "Ron Levi",
  "labeled_on": "2026-10-24",
  "blind": true,
  "description": "Phase 3 vaccine efficacy protocol, v6.0. Public registry document, no committee appendices.",
  "expected_decision": "RETURNED_ADMIN",
  "expected_findings": [
    {
      "domain": "administrative",
      "category": "MISSING_CONSENT_FORM",
      "guideline_ref": "ADMIN-CHK-06",
      "page": 0,
      "severity": "critical",
      "note": "No informed consent form or appendix referenced anywhere."
    },
    {
      "domain": "scientific",
      "category": "INCONSISTENT_SAMPLE_SIZE",
      "guideline_ref": "SPIRIT-19",
      "page": 47,
      "quote": "approximately 30,000 participants",
      "severity": "major",
      "note": "Synopsis says 30,000; section 9.2 says 30,420."
    }
  ]
}
```

**Field rules**

| Field | Required | Values |
|---|---|---|
| `domain` | yes | `administrative` or `scientific` |
| `category` | yes | one canonical code from the list below (the alias map handles LLM wording) |
| `guideline_ref` | yes | `ADMIN-CHK-01..15`, `SPIRIT-1a..34` (with applicable sub-items a/b/c/d; refer to spirit_2025_items.json), `GCP-01..12` |
| `page` | yes | 1-based page in the PDF where the problem is visible; `0` when the item is absent from the whole document |
| `quote` | recommended | verbatim text from that page (helps the 30-finding check later) |
| `severity` | yes | `critical`, `major`, `minor` |
| `note` | yes | one sentence: what is wrong, in your words |

`expected_decision`: what the system should say under the current rules: `RETURNED_ADMIN` when any
administrative finding exists (most public protocols), otherwise `PASS` / `NEEDS_HUMAN_REVIEW` /
`MAJOR_CONCERNS` by the hybrid rule (verified critical → MAJOR; score ≥ 90 PASS, 70-89 HUMAN, < 70 MAJOR;
score = 100 − 25 per critical − 10 per major − 3 per minor).

**Canonical categories** (use these; add a new one only together with an alias entry in
`eval/category_aliases.json`):

*Administrative:* `UNREADABLE_PDF`, `MISSING_TITLE`, `MISSING_VERSION`, `MISSING_DATE`,
`MISSING_REGISTRY_ID`, `MULTIPLE_REGISTRY_IDS`, `MISSING_PI`, `MISSING_SPONSOR`,
`MISSING_CONSENT_FORM`, `MISSING_INSURANCE`, `MISSING_ETHICS_STATEMENT`, `MISSING_SIGNATURE_PAGE`,
`MISSING_CONTACT`, `MISSING_SECTION`, `MISSING_DOCUMENT`, `FORMAT_ISSUE`, `INTERNAL_CONTRADICTION`.

*Scientific:* `INCONSISTENT_SAMPLE_SIZE`, `NO_SAMPLE_SIZE`, `NO_SAMPLE_SIZE_JUSTIFICATION`,
`RANDOMIZATION_METHOD_UNSPECIFIED`, `BLINDING_UNSPECIFIED`, `NO_PRIMARY_OUTCOME`,
`NO_STATISTICAL_PLAN`, `NO_DATA_MONITORING`, `NO_HARMS_PLAN`, `NO_STOPPING_RULES`,
`INCONSISTENT_AGE_RANGE`, `INCONSISTENT_PHASE`, `REGISTRY_NOT_FOUND`, `REGISTRY_MISMATCH`,
`INTERNAL_CONTRADICTION`, `METHOD_UNSPECIFIED`, `SAFETY_GAP`, `ETHICS_GAP`, `CONSENT_GAP`, `OTHER`.

**How to label a protocol (about 60-90 minutes each)**

1. Open the PDF and the ClinicalTrials.gov record side by side.
2. Administrative pass: go through `knowledge_base/administrative/admin_checklist.md` item by item
   (ADMIN-CHK-01 to 15). Every failed item = one finding with that code.
3. Scientific pass: go through `knowledge_base/scientific/spirit_checklist.md` item by item. Every
   SPIRIT item not addressed, or addressed inconsistently in two places, = one finding.
4. Registry pass: compare enrollment, phase, primary outcomes, interventions, conditions, sponsor
   with the registry record. Every discrepancy = `REGISTRY_MISMATCH` with `SPIRIT-4`.
5. Write the JSON, commit it. Only then may the system be run on that protocol.

Label what a careful committee member would raise, not everything that could be said. When unsure
whether something is a finding, record it with `severity: "minor"` and say so in `note`.

---

## 3. Knowledge base verification

Two files, both currently drafts written from memory and marked as such:

- `knowledge_base/scientific/spirit_checklist.md`: check every item and its numbering against the
  official SPIRIT 2025 statement (BMJ 2025). Fix wording, add missing items, keep the code format
  `SPIRIT-nn` / `SPIRIT-nna` because findings cite it. SPIRIT 2025 is now the code set; keep the locked matching algorithm
  and note the official number in the text.
- `knowledge_base/administrative/admin_checklist.md`: check the 15 items against the committee SOP
  (or the Ministry of Health Helsinki procedure). Add or remove items; keep codes stable
  (`ADMIN-CHK-16`, … for new ones).
- `knowledge_base/scientific/ich_gcp_key_points.md`: verify against ICH E6(R3).

Remove the "draft / to be verified" banners when done, and add a line "Verified against <source,
version, date> by Ron Levi".

---

## 4. The 30-finding human check (after the ablation run)

Path: `eval/human_check/verified_findings_check.csv`. Amir generates the 30 rows (a random sample of
`verified` findings of the full system across all protocols, ids, page, quote, guideline); you fill
the last two columns **without** looking at the finding's explanation first, only at the PDF page:

| run_id | finding_id | case_id | page | quote | guideline_ref | supports (yes / partly / no) | comment |
|---|---|---|---|---|---|---|---|

"yes" = the quoted passage on that page really shows the problem the finding describes;
"partly" = the passage is relevant but the conclusion overreaches; "no" = the passage does not
support it or is not on that page. The result is reported as yes / partly / no counts with the
"no" rows listed.

---

## Checklist before 30 October

- [x] `eval/protocols/SOURCES.md` + `protocol_sources.csv` committed (2026-10-26); the PDFs are not committed -
      `python eval/protocols/fetch_protocols.py` rebuilds them from ClinicalTrials.gov
- [x] dev / eval split in `SOURCES.md` (3 dev / 16 eval); Ron's five labeled protocols are all evaluation protocols
- [x] five blind label files committed 2026-10-29 (`nct01977547`, `nct04084990`, `nct05199324`, `nct05698277`,
      `nct06846736`; 46 findings) - reduced-scope plan, objective text-level findings only
- [x] live ablation run 2026-10-29 (`reports/results.md`, `reports/CP2_SUMMARY.md`)
- [x] `eval/human_check/verified_findings_check.csv` generated (30 rows, full system) - Ron fills the last two columns
- [ ] domain correction of the 16 data-management / monitoring / confidentiality labels (proposed to Ron 2026-10-29);
      afterwards `python eval/rescore.py`
- [ ] `eval/labeled_cases/<case_id>.json` for every protocol, committed **before** any run
- [ ] `eval/category_aliases.json` extended if you used a new category
- [ ] knowledge base verified, banners removed
- [ ] `eval/human_check/verified_findings_check.csv` filled
