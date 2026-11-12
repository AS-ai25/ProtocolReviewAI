# Human Evaluation: pre-submission quality audit

> Review date: 12 November 2026. This is an audit of the submitted human-review spreadsheets, not an independent expert adjudication of clinical validity.

## Files and integrity

| Artifact | Rows | Status |
|---|---:|---|
|Original full-system evidence recheck | 30 | Complete; source columns preserved in supplied CSV |
|Unmatched full-system findings | 40 | All classification and comments populated; source fields match the raw CSV |
|Full-system tool-calling evidence check | 30 | Both evidence support and claim correctness fields populated |
|Matched-reference list | 38 | Used as comparison-only reference, not as a new gold standard |

## Unmatched findings summary

- **31** classified `true but unlabeled`
- **5** classified `wrong`
- **4** classified `cannot tell`
- **0** classified `duplicate of a matched finding`

The submitted reference crosscheck identified **no confirmed exact duplicate** and **five thematic-overlap pairs requiring review**. This is not a proof that duplicate subclaims are absent. Pairing uses the same protocol ID and the complete title/description where available. Duplicate status is not inferred from an identical category or guideline code alone.

### Overlap pairs to check with Amir

| Unmatched finding | Reference finding | Why this is not yet a confirmed duplicate |
|---|---|---|
| `nct04084990 / SCI-L011` | `SCI-R001` | שני הממצאים קשורים לגודל המדגם. R001 הוא טענה כללית על מספרים לא עקביים; L011 הוא טענה ספציפית על תוספת נשירה ועל מקור הנחות השונות. אין די בכותרת R001 כדי לשלול חפיפה חלקית, אך אין זהות ברורה. |
| `nct04084990 / SCI-L014` | `SCI-L004` | קרבה בתחום הבטיחות: L004 מתאר היעדר DSMB/כללי עצירה וניטור; L014 מתאר הגדרת AE/SAE, איסוף נזקי אם/עובר/יילוד ודיווח. יתכן חפיפה מסוימת בניסוח, אך ליבת הבעיה שונה. |
| `nct04084990 / SCI-L017` | `SCI-L001` | יש חפיפה נושאית: L001 מערער על הסמיות בהשוואה ללא sham; L017 טוען גם לפער בין רישום המחקר לפרוטוקול לגבי masking, מכשיר ושלב. רכיב הסמיות יכול לחפוף, אבל הממצא הכולל אינו העתק; השוואת רישום דורשת מקור חיצוני. |
| `nct05199324 / SCI-L026` | `SCI-L007` | קרבה בתחום זכאות: L007 עוסק בסתירה בין תקציר לגוף לגבי polymicrobial; L026 בהגדרות תפעוליות של כמה מונחי זכאות. עשויה להיות חפיפה נקודתית בלבד, לא אותה טענה. |
| `nct06846736 / SCI-L009` | `SCI-L013` | שניהם עוסקים בזכאות למחקר. L009 מתייחס להגדרות תפעוליות של בדיקת ALK ואיכות חומר, בעוד L013 מתייחס להטיית בחירה הנובעת מקריטריון המעקב. קיימת קרבה נושאית, אך אין כפילות מלאה מוכחת. |

### Substantive findings requiring explicit attention (14 review flags, including overlap cases)

These points are **review flags**, not forced replacements for the existing classification. The current labels remain untouched.

| Protocol / Finding | Current classification | Concern to resolve |
|---|---|---|
| `nct01977547 / SCI-L004` | `true but unlabeled` | **Review wording:** הספים המנהליים אינם בעצמם הוכחה לפגם בטיחותי; להבחין בין omission לסיכון. |
| `nct01977547 / SCI-L006` | `true but unlabeled` | **Review substantive inference:** השוואת 1.7% ל-7/91 עלולה לערבב אי-היענות עם אי-קבלת עירוי. |
| `nct01977547 / SCI-L015` | `true but unlabeled` | **Benchmark chronology:** מותר לכלול את פרוטוקול 2017 בהשוואה מול SPIRIT 2025 במסגרת ניסוי הערכה עקבי; יש לתאר זאת כ-benchmark רטרוספקטיבי, ולא כטענה להפרת חובה שהייתה בתוקף בשנת 2017. |
| `nct04084990 / SCI-L008` | `true but unlabeled` | **Composite finding:** הכותרת משלבת SPIRIT/פיצוי/פרטי גרסה. לא כל רכיב מוכח באותה רמה. |
| `nct04084990 / SCI-L014` | `true but unlabeled` | **Overlap to resolve:** בחינה נפרדת מול SCI-L004 התואם: ניטור לעומת דיווח AE; לא לקבוע כפילות כוללת. |
| `nct04084990 / SCI-L017` | `cannot tell` | **Overlap + external dependency:** רכיב masking קרוב ל-SCI-L001, אך מכשיר/Registry דורשים רשומה חיצונית מתוארכת. |
| `nct05199324 / SCI-L002` | `true but unlabeled` | **Non-inferiority margin requires expert judgment:** המרווח המוחלט המוצהר הוא 6%. אם סיכון התמותה בביקורת הוא 8%, מרווח זה מאפשר עד 14% בזרוע הניסוי במסגרת גבול אי-הנחיתות. זה מעלה שאלה לגבי משמעות קלינית והנמקה של המרווח, אך אינו מוכיח כשלעצמו שמרווח 6% פסול. יש להבחין בין חשש לגבי הצדקת המרווח לבין הכרעה של מומחה סטטיסטי/קליני. |
| `nct05199324 / SCI-L026` | `true but unlabeled` | **Overlap to resolve:** יש לבדוק בנפרד מול SCI-L007: חוסר תפעוליות זכאות אינו בהכרח סתירה בקריטריון polymicrobial. |
| `nct05698277 / SCI-L005` | `true but unlabeled` | **Observational-study applicability:** לבדוק אם טענת AE/SAE מתאימה למחקר תצפיתי ללא התערבות ניסויית. אפשר להעיר על חוסר בהסבר על סיכונים הקשורים להליך המחקר, אך אין להחיל באופן אוטומטי כל חובת דיווח של ניסוי התערבותי. |
| `nct05698277 / SCI-L012` | `true but unlabeled` | **Observational-study applicability:** אין להסיק ש-DSMB נדרש במחקר תצפיתי. יש להעריך אם מתוארים פיקוח, ניהול נתונים ובטיחות פרוצדורלית הרלוונטיים לסוג המחקר; חוסר פירוט אינו שווה אוטומטית אי-ציות. |
| `nct06846736 / SCI-L005` | `true but unlabeled` | **Methodological risk, not observed leakage:** פיצול אקראי ברמת מקרה בין מרכזים עשוי ליצור תלות במאפייני אתר או סורק, אם לא בוצעה בדיקה נפרדת של הכללה למרכזים חדשים. היעדר תכנית leave-centre-out הוא פער בתכנון ההערכה, אך אינו מוכיח דליפת מידע, הטיית אתר בפועל או ניפוח תוצאות. |
| `nct06846736 / SCI-L009` | `true but unlabeled` | **Overlap to resolve:** השוואה מול SCI-L013: נושאים שונים של eligibility, אך יש לבדוק תתי-טענות. |
| `nct06846736 / SCI-L010` | `cannot tell` | **External verification needed:** טענת כרונולוגיית הרישום דורשת מקור תאריך והיסטוריית פרוטוקול. |
| `nct06846736 / SCI-L020` | `cannot tell` | **Approval vs documentation:** היעדר פירוט היקף אישור אינו מוכיח היעדר אישור מרכז מתאם בפועל. |

## Important methodological limitations

- The 40 findings are a sample of unmatched findings, not a complete estimate of all false positives.
- Several finding descriptions contain multiple claims; a single binary label can conceal mixed correctness. The comments must qualify what was and was not verified.
- A missing statement in a protocol PDF does not establish that required information is absent from the broader submission package.
- Do not apply requirements specific to randomized interventional trials automatically to retrospective or observational studies.
- `true but unlabeled` means the reviewer considered a finding not represented in the matched reference, **not** a formally adjudicated clinical defect.
- `cannot tell` is appropriate when confirmation depends on trial registry history, consent forms, ethics approvals, source data or expert judgment unavailable in the supplied PDFs.
- The original blind labels were not changed; this review is a separate post-hoc assessment.

## Before interpreting the results

1. Confirm the five overlap pairs with the exact underlying model claims, not titles alone.
2. Revisit flagged composite findings and document which subclaims are actually supported.
3. Obtain expert adjudication where scientific/ethical applicability materially changes a conclusion.
4. Report counts explicitly as **reviewer classifications**, not validated precision, and include uncertainty.
5. Maintain the current CSVs as immutable submitted drafts until the final reviewer decides whether to revise specific cells.

## Clarifications adopted after reviewer discussion (12 November 2026)

1. **Historical protocols are allowed in the sample.** The 2017 ABC PICU protocol can be evaluated with the same SPIRIT 2025 benchmark as the other protocols to maintain comparability in this limited test set. This is a retrospective reporting-gap assessment, not a regulatory non-compliance conclusion about the year 2017. No exclusion or automatic relabeling is required purely because of publication year.
2. **INVEST and the 6% margin:** This flag asks whether the *clinical acceptability and justification* of the non-inferiority margin are sufficiently substantiated. It does **not** conclude that the 6% margin is scientifically invalid. The 8% to 14% illustration describes the maximum mortality rate compatible with an absolute six-percentage-point margin, not observed trial mortality. Expert evaluation is needed for any categorical verdict.
3. **ALK and centre effects:** Treat site-related technical confounding and absent leave-centre-out evaluation as *potential threats to generalisability*. No claim of actual data leakage or performance inflation is supported from the protocol alone.
4. **Fetal Cardiac is observational:** Interpret the applicability of SPIRIT RCT-specific requirements carefully. Distinguish meaningful documentation improvements from mandatory requirements, and avoid interpreting missing DSMB as a confirmed defect.
5. **Overlap list corrected:** The fifth flagged pair is `nct06846736 / SCI-L009` versus `SCI-L013` (ALK), consistent with the actual spreadsheet. The previously listed `nct05698277 / SCI-L009` versus `SCI-L013` (Fetal Cardiac) is a *separate thematic comparison* noted as nonduplicate, not one of the five flagged overlap pairs.
6. **No source-label edits:** These are interpretive clarifications for the audit and optional reviewer notes. All original blind labels and submitted classification cells remain unchanged.
