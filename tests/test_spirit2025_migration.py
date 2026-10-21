"""Guard against accidental SPIRIT-2013 citations after migrating check rules."""
import re
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]

def test_rule_citations_are_2025_codes():
    text=(ROOT/'src/protocol_review/tools/checks.py').read_text(encoding='utf8')
    refs=set(re.findall(r'"(SPIRIT-\d{1,2}[a-d]?(?:; SPIRIT-\d{1,2}[a-d]?)*)"',text))
    known={x['code'] for x in json.loads((ROOT/'knowledge_base/scientific/spirit_2025_items.json').read_text())['items']}
    for ref in refs:
        assert all(r in known for r in ref.split('; ')), ref
    assert '"SPIRIT-14"' not in text
    assert '"SPIRIT-02"' not in text

def test_complete_spirit2025_catalog():
    entries=json.loads((ROOT/'knowledge_base/scientific/spirit_2025_items.json').read_text())['items']
    ids={e['id'] for e in entries}
    assert {str(i) for i in range(1,35)} == {re.match(r'\d+',id).group() for id in ids}
    assert len(ids)==len(entries)
    assert {'14a','19','21a','22','24a','27d','34'} <= ids

def test_matching_accepts_new_subitems():
    from eval.matching import _refs
    assert 'SPIRIT-27D' in _refs('SPIRIT-27d')
    assert 'SPIRIT-24C' in _refs('SPIRIT-24c')
