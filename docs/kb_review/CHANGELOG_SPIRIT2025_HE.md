# סיכום שינויים ל-SPIRIT 2025

## קבצים קיימים שעודכנו

- `src/protocol_review/tools/checks.py`: התאמת ההפניות של הכללים הדטרמיניסטיים למזהי SPIRIT 2025. לדוגמה, גודל מדגם מופנה לסעיף 19, תוצא ראשי לסעיף 16, וניתוח סטטיסטי לסעיף 27a. לא שונו תנאי הכללים או חומרתם. בדיקת רנדומיזציה קיימת עדיין משלבת שני נושאים, יצירת רצף והסתרת הקצאה, ולכן מפנה לשניהם.
- `src/protocol_review/agents/base.py`, `src/protocol_review/knowledge_base.py` ו-`eval/matching.py`: הרחבת זיהוי מזהי תתי סעיפים, לרבות האות d. כלל ההתאמה הנעול של ההערכה נשאר ללא שינוי.
- `src/protocol_review/agents/prompts.py` ו-`src/protocol_review/state.py`: התאמת דוגמאות והנחיות להפניות מעודכנות.
- `src/protocol_review/agents/scientific_reviewer.py`: שימוש באיתותים מכלי איתור פרקי הפרוטוקול.
- `knowledge_base/scientific/spirit_checklist.md`: רשימת SPIRIT 2025 במקום המיפוי הישן.
- `eval/LABELING_GUIDE.md` ו-`eval/labeled_cases/_TEMPLATE.json`: הסברים ודוגמה לתיוג חדש לפי 2025. תיוגים ישנים לא שונו בדיעבד.

## קבצים חדשים

- `knowledge_base/scientific/spirit_2025_items.json`: פריטים ותתי סעיפים, שאלות לבדיקה ותחולה אפשרית.
- `src/protocol_review/tools/section_coverage.py`: איתור ראשוני של פרקים, לרבות תנאי הכללה ואי הכללה.
- `knowledge_base/scientific/section_coverage_review.md`: הנחיות לסוכן להבחין בין כותרת חסרה לבין תוכן חסר.
- `tests/test_section_coverage.py` ו-`tests/test_spirit2025_migration.py`: בדיקות ממוקדות.
- `eval/spirit_legacy_labels_inventory.json`: רשימה של תוויות ישנות הדורשות עיון, מבלי לשנות אותן.
- `docs/kb_review/`: שתי טיוטות PDF לעיון מקצועי. הן אינן מחליפות קובצי ידע פעילים בקוד.

## מה עדיין פתוח

1. אישור מקצועי של בסיסי הידע מול המקורות העדכניים ותנאי התחולה, בפרט מחקרים שאינם ניסויים אקראיים.
2. בדיקה שכל ארבע תצורות ההשוואה מקבלות אותם מקורות מידע וכלי אימות.
3. הרצת בדיקות רגרסיה מלאות והרצת LLM על מסמכים אמיתיים.
4. תיוג עיוור ואימות אנושי של הממצאים.
5. בדיקה אפשרית של מנגנון Matching בהקשר לכפילויות, בלי לשנות את המדד הנעול ללא תיעוד.

הקבצים מיועדים לסקירה משותפת לפני שילוב בגיט. אין בחבילה טענה שהמערכת בודקת כל סעיף של SPIRIT 2025 בצורה מלאה או מאומתת.
