"""Test configuration: isolated SQLite DB + output dir, NO_LLM default, sample PDFs."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

_TMP = Path(tempfile.mkdtemp(prefix="protocol_review_tests_"))
os.environ.update({
    "DATABASE_URL": f"sqlite:///{(_TMP / 'test.db').as_posix()}",
    "OUTPUT_DIR": str(_TMP / "outputs"),
    "EMAIL_DRY_RUN": "true",
    "NO_LLM": "true",
    "WEBHOOK_SECRET": "test-secret",
    "ANTHROPIC_API_KEY": "sk-test-not-used",
    "MAX_REVISE_ROUNDS": "1",
})

import pytest  # noqa: E402

from protocol_review import db  # noqa: E402

SAMPLES = ROOT / "samples"


@pytest.fixture(scope="session", autouse=True)
def _samples():
    if not (SAMPLES / "synthetic_protocol_good.pdf").exists() or not (SAMPLES / "synthetic_protocol_flawed.pdf").exists():
        sys.path.insert(0, str(SAMPLES))
        import make_sample_protocols  # type: ignore
        make_sample_protocols.main()
    yield


@pytest.fixture(scope="session", autouse=True)
def _db():
    db.reset_engine_for_tests(os.environ["DATABASE_URL"])
    yield


@pytest.fixture
def good_pdf() -> Path:
    return SAMPLES / "synthetic_protocol_good.pdf"


@pytest.fixture
def flawed_pdf() -> Path:
    return SAMPLES / "synthetic_protocol_flawed.pdf"


REGISTRY_FIXTURE = {
    "protocolSection": {
        "identificationModule": {"nctId": "NCT04470427", "officialTitle": "A Phase 3, Randomized, Observer-Blind, Placebo-Controlled Study of VX-101"},
        "statusModule": {"overallStatus": "COMPLETED", "startDateStruct": {"date": "2026-10-01"}},
        "designModule": {"studyType": "INTERVENTIONAL", "phases": ["PHASE3"], "enrollmentInfo": {"count": 30415},
                         "designInfo": {"allocation": "RANDOMIZED", "maskingInfo": {"masking": "QUADRUPLE"}}},
        "conditionsModule": {"conditions": ["Respiratory Infection"]},
        "armsInterventionsModule": {"interventions": [{"name": "VX-101"}, {"name": "Placebo"}]},
        "outcomesModule": {"primaryOutcomes": [{"measure": "Laboratory-confirmed symptomatic disease"}]},
        "sponsorCollaboratorsModule": {"leadSponsor": {"name": "Helix Biologics Ltd."}},
    }
}


@pytest.fixture
def registry_fetch():
    return lambda nct: REGISTRY_FIXTURE
