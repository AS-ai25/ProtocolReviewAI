"""Download the real-protocol test set from the public ClinicalTrials.gov document store.

    python eval/protocols/fetch_protocols.py            (skips files already present with the right size)
    python eval/protocols/fetch_protocols.py --force

The PDFs are not committed to the repository: they are public registry documents, but most carry a sponsor
confidentiality header, so the repository keeps the links (protocol_sources.csv, SOURCES.md) and this script
rebuilds `eval/protocols/<nct_id>.pdf` on demand. The expected byte sizes were recorded on 2026-10-26/27 when the
files were downloaded and compared with the copies the team received.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import httpx

HERE = Path(__file__).resolve().parent
SOURCES = HERE / "protocol_sources.csv"
EXPECTED_SIZE = {
    "NCT03390257": 2458915, "NCT03503812": 1219183, "NCT03504189": 1086239, "NCT04002830": 1832259,
    "NCT04084990": 688592, "NCT04179786": 1869808, "NCT04186247": 1388357, "NCT04202887": 275343,
    "NCT04348656": 1266473, "NCT04523324": 440836, "NCT05199324": 595651, "NCT05796557": 2181984,
    "NCT06846736": 587133, "NCT07095049": 2859367, "NCT07183462": 186123, "NCT07199218": 1685885,
    "NCT07328308": 198399,
    # added 2026-10-27 (Ron's second batch)
    "NCT01977547": 1157550, "NCT05698277": 712639,
}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--force", action="store_true", help="re-download even when the file is present")
    ap.add_argument("--out", default=str(HERE))
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader(SOURCES.open(encoding="utf-8-sig")))
    bad = 0
    with httpx.Client(timeout=60, follow_redirects=True, headers={"User-Agent": "ProtocolReviewAI/0.1"}) as client:
        for r in rows:
            nct, url = r["NCT_ID"].strip(), r["Public_PDF_URL"].strip()
            dst = out / f"{nct.lower()}.pdf"
            want = EXPECTED_SIZE.get(nct)
            if dst.exists() and not a.force and (want is None or dst.stat().st_size == want):
                print(f"ok      {dst.name} ({dst.stat().st_size:,} bytes)")
                continue
            try:
                resp = client.get(url)
                resp.raise_for_status()
            except Exception as exc:  # network / HTTP
                print(f"FAILED  {dst.name}: {exc}")
                bad += 1
                continue
            dst.write_bytes(resp.content)
            size = len(resp.content)
            flag = "" if want is None or size == want else f"  (size differs from the recorded {want:,}: the registry may hold a newer upload)"
            print(f"fetched {dst.name} ({size:,} bytes){flag}")
    print(f"\n{len(rows) - bad}/{len(rows)} protocols present in {out}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
