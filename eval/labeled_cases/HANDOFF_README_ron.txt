DS23 - Blind manual labels / Git handoff (29 October 2026)

Five JSON files to place at eval/labeled_cases/<case_id>.json. Commit BEFORE running ablation.
Source: the user's most recent labeling workbook (_DS23 - תיוג ידני(1).xlsm), via the previously generated technical extraction. No agent outputs, auto-drafts, or system findings were consulted.
All 46 original quote/note/category/severity/domain/guideline_ref values preserved byte-for-byte as Unicode strings. Multi-code guideline_ref strings deliberately preserved: matching.py supports them.
20 non-integer multi-page locations were mapped to the FIRST indicated PDF page for the required integer page field. The EXACT original page notation is retained in source_pages_original; this is an extra provenance field, not an annotation change. The reviewer should be aware that only the first page participates in page-based matching.
PASS checks (15) and PENDING items (3) are excluded from expected_findings; keep the original workbook separately.

DECISION POLICY: expected_decision = RETURNED_ADMIN in each case, mechanically derived from the project's LOCKED policy because each case contains >=1 administrative label. This is not a clinical approval or a claim of missing documents in a full Helsinki submission. Under force_scientific, scientific output is evaluated separately. Do NOT replace these decision labels with NEEDS_HUMAN_REVIEW solely because expert adjudication is unavailable; discuss any change in evaluation scope with Amir.

blind=true is copied from the annotator's workbook. These labels were not independently expert-adjudicated, notwithstanding the user's own objective verification. No scientific correctness validation performed by the converter.
