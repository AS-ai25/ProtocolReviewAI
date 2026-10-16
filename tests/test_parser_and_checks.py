from protocol_review.pdf_parser import parse_pdf
from protocol_review.tools import checks, clinicaltrials
from protocol_review.baseline import run_baseline


def test_metadata_extraction(good_pdf):
    parsed = parse_pdf(good_pdf)
    m = parsed["protocol_meta"]
    assert m["nct_id"] == "NCT04470427"
    assert m["version"] == "2.0"
    assert "Dana Cohen" in m["principal_investigator"]
    assert "Helix" in m["sponsor"]
    assert m["phase"] == "3"
    assert not m["likely_scanned"]
    assert "=== PAGE 1 ===" in parsed["pdf_text"]


def test_good_protocol_has_no_rule_findings(good_pdf, registry_fetch):
    res = run_baseline(good_pdf, registry_fetch=registry_fetch, write=False)
    cats = [f["category"] for f in res["findings"]]
    assert cats == [], cats
    assert res["decision"] == "PASS"


def test_flawed_protocol_rule_findings(flawed_pdf, registry_fetch):
    res = run_baseline(flawed_pdf, registry_fetch=registry_fetch, write=False)
    cats = {f["category"] for f in res["findings"]}
    expected = {"MISSING_CONSENT_FORM", "MISSING_INSURANCE", "MISSING_SIGNATURE_PAGE", "MISSING_SECTION",
                "INCONSISTENT_SAMPLE_SIZE", "NO_SAMPLE_SIZE_JUSTIFICATION", "RANDOMIZATION_METHOD_UNSPECIFIED",
                "NO_STATISTICAL_PLAN", "INCONSISTENT_AGE_RANGE", "INCONSISTENT_PHASE"}
    assert expected <= cats, expected - cats
    assert res["decision"] == "RETURNED_ADMIN"
    assert all(f["source"] == "rule" and f["status"] == "verified" for f in res["findings"])


def test_sample_size_ignores_prior_studies():
    text = "Phase 1/2 studies (n = 600) were positive. A total of 30,415 participants will be randomized (n = 30,415)."
    assert set(checks.sample_sizes(text)) == {30415}
    assert checks.phases_mentioned("A Phase 3 trial. Phase 1/2 studies showed safety. phase III design.") == {"3"}


def test_registry_mismatch_enrollment(flawed_pdf):
    reg = clinicaltrials.parse_study("NCT04470427", {"protocolSection": {"designModule": {"phases": ["PHASE3"], "enrollmentInfo": {"count": 500}}}})
    parsed = parse_pdf(flawed_pdf)
    out = checks.registry_checks(parsed["pages"], parsed["protocol_meta"], reg.model_dump())
    assert any(f["category"] == "REGISTRY_MISMATCH" and "Enrollment" in f["title"] for f in out)


def test_registry_lookup_handles_errors():
    def boom(nct):
        raise RuntimeError("offline")
    rec = clinicaltrials.lookup("NCT00000000", fetch=boom)
    assert rec.found is False and "offline" in rec.error
    assert clinicaltrials.lookup("", fetch=boom).error == "no NCT id"
