"""Dashboard page, statistics endpoints and the run summary."""
from fastapi.testclient import TestClient

from protocol_review.api import app
from protocol_review.config import settings

HDR = {"X-Webhook-Secret": settings.webhook_secret}


def test_dashboard_and_stats_endpoints(flawed_pdf):
    client = TestClient(app)
    page = client.get("/dashboard")
    assert page.status_code == 200 and "<html" in page.text.lower() and "/stats/trace/" in page.text

    with open(flawed_pdf, "rb") as fh:
        r = client.post("/webhook/protocol", headers=HDR, files={"file": ("p.pdf", fh, "application/pdf")},
                        data={"nct_id": "NCT04470427", "force_scientific": "true"})
    assert r.status_code == 200
    run_id = r.json()["run_id"]

    s = client.get(f"/runs/{run_id}/summary").json()
    assert s["status"] == "done" and s["decision"] and s["n_findings"] > 0 and s["force_scientific"] is True
    assert "verified" in s["by_status"] and s["reports"]["final"].endswith("kind=final")
    assert s["cost"]["llm_calls"] >= 1
    assert s["protocol_meta"]["nct_id"] == "NCT04470427"

    tr = client.get(f"/stats/trace/{run_id}").json()
    kinds = {e["kind"] for e in tr}
    assert {"message", "llm_call"} <= kinds and all(e["t"] for e in tr)

    u = client.get(f"/stats/usage", params={"run": run_id, "by": "agent"}).json()
    assert u["runs"] == 1 and u["total"]["calls"] >= 1
    assert client.get("/stats/usage", params={"by": "bogus"}).status_code == 400
    c = client.get("/stats/communications", params={"run": run_id}).json()
    assert c["messages_per_run"]["runs"] == 1 and c["calls_per_run"]["max"] >= 1
    assert client.get("/runs/nope/summary").status_code == 404
