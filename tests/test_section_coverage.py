import unittest
from protocol_review.tools.section_coverage import coverage_screen, spirit_2025_catalog_screen

class TestScientificCoverage(unittest.TestCase):
    def test_independent_inclusion_exclusion(self):
        rows=coverage_screen([{"page":1,"text":"Inclusion Criteria\nAdults ages 18-65\nStudy Design\nRandomised trial"}])
        lookup={r['key']:r for r in rows}
        self.assertEqual(lookup['inclusion']['status'],'heading_detected')
        self.assertEqual(lookup['exclusion']['status'],'needs_manual_review')
    def test_narrative_not_heading(self):
        rows=coverage_screen([{"page":1,"text":"The inclusion criteria are described in a supplement to the study report.\n"}])
        self.assertIn(next(x for x in rows if x['key']=='inclusion')['status'],('mentioned_only','needs_manual_review'))
    def test_nonrandomized_applicability(self):
        rows=coverage_screen([{"page":1,"text":"Background\nExample"}], randomized=False)
        self.assertEqual(next(x for x in rows if x['key']=='randomization')['status'],'not_applicable')

    def test_official_2025_ids(self):
        rows=coverage_screen([{"page":1,"text":"Objectives\nInformed Consent\nTrial Design"}])
        indexed={r["key"]:r["spirit_2025_item"] for r in rows}
        self.assertEqual(indexed["objectives"],"10")
        self.assertEqual(indexed["consent"],"32a")
    def test_full_catalog(self):
        rows=spirit_2025_catalog_screen([{"page":1,"text":"Inclusion Criteria"}],randomized=True)
        ids={r["code"] for r in rows}
        self.assertTrue(all("SPIRIT-"+str(i) in ids or any(k.startswith("SPIRIT-"+str(i)+s) for k in ids for s in 'abcd') for i in range(1,35)))
        self.assertIn('SPIRIT-14a',ids)
        self.assertIn('SPIRIT-34',ids)

if __name__ == '__main__': unittest.main()
