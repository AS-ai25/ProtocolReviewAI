"""ClinicalTrials.gov API v2 lookup by NCT ID (the "scientific metadata" source)."""
from __future__ import annotations

import logging
from typing import Callable

import httpx

from ..config import settings
from ..state import RegistryRecord

log = logging.getLogger(__name__)
CTGOV_URL = "https://clinicaltrials.gov/api/v2/studies/{nct}"

Fetcher = Callable[[str], dict]


def _default_fetch(nct_id: str) -> dict:
    with httpx.Client(timeout=settings.clinicaltrials_timeout, headers={"User-Agent": "ProtocolReviewAI/0.1"}) as c:
        r = c.get(CTGOV_URL.format(nct=nct_id), params={"format": "json"})
        r.raise_for_status()
        return r.json()


def parse_study(nct_id: str, data: dict) -> RegistryRecord:
    ps = data.get("protocolSection", {}) or {}
    ident = ps.get("identificationModule", {}) or {}
    design = ps.get("designModule", {}) or {}
    status = ps.get("statusModule", {}) or {}
    cond = ps.get("conditionsModule", {}) or {}
    arms = ps.get("armsInterventionsModule", {}) or {}
    outcomes = ps.get("outcomesModule", {}) or {}
    sponsor = ((ps.get("sponsorCollaboratorsModule", {}) or {}).get("leadSponsor", {}) or {}).get("name", "")
    phases = design.get("phases") or []
    return RegistryRecord(
        nct_id=nct_id,
        found=True,
        title=ident.get("officialTitle") or ident.get("briefTitle") or "",
        phase=", ".join(p.replace("PHASE", "").strip() for p in phases) if phases else "",
        status=status.get("overallStatus", ""),
        enrollment=(design.get("enrollmentInfo", {}) or {}).get("count"),
        conditions=list(cond.get("conditions") or []),
        interventions=[iv.get("name", "") for iv in arms.get("interventions") or []],
        primary_outcomes=[o.get("measure", "") for o in outcomes.get("primaryOutcomes") or []],
        sponsor=sponsor,
        raw={"studyType": design.get("studyType", ""), "allocation": (design.get("designInfo", {}) or {}).get("allocation", ""),
             "masking": ((design.get("designInfo", {}) or {}).get("maskingInfo", {}) or {}).get("masking", ""),
             "startDate": (status.get("startDateStruct", {}) or {}).get("date", "")},
    )


def lookup(nct_id: str, fetch: Fetcher | None = None) -> RegistryRecord:
    """Fetch and normalise a study; never raises (errors land in `.error`)."""
    if not nct_id:
        return RegistryRecord(nct_id="", found=False, error="no NCT id")
    fetch = fetch or _default_fetch
    try:
        return parse_study(nct_id, fetch(nct_id))
    except httpx.HTTPStatusError as exc:
        return RegistryRecord(nct_id=nct_id, found=False, error=f"HTTP {exc.response.status_code}")
    except Exception as exc:  # network, JSON, ...
        log.warning("ClinicalTrials.gov lookup failed for %s: %s", nct_id, exc)
        return RegistryRecord(nct_id=nct_id, found=False, error=str(exc)[:200])


def registry_summary(rec: dict) -> str:
    if not rec or not rec.get("found"):
        return f"ClinicalTrials.gov record: NOT AVAILABLE ({(rec or {}).get('error', 'no NCT id')})"
    lines = [
        f"ClinicalTrials.gov record for {rec['nct_id']}:",
        f"- Official title: {rec.get('title')}",
        f"- Phase: {rec.get('phase') or 'n/a'} | Status: {rec.get('status')}",
        f"- Enrollment (planned/actual): {rec.get('enrollment')}",
        f"- Conditions: {', '.join(rec.get('conditions') or [])}",
        f"- Interventions: {', '.join(rec.get('interventions') or [])}",
        f"- Primary outcomes: {' | '.join(rec.get('primary_outcomes') or [])}",
        f"- Lead sponsor: {rec.get('sponsor')}",
        f"- Design: {rec.get('raw', {})}",
    ]
    return "\n".join(lines)
