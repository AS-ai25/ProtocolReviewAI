"""Dashboard page, statistics endpoints and the run summary."""
from fastapi.testclient import TestClient

from protocol_review.api import app
from protocol_review.config import settings

HDR = {"X-Webhook-Secret": settings.webhook_secret}


def test_dashboard_and_stats_endpoints(flawed_pdf):
    client = TestClient(app)
    page = client.get("/dashboard")
    assert client.get("/", follow_redirects=False).status_code in (302, 307) and client.get("/favicon.ico").status_code == 204
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
    assert {"message", "llm_call", "step"} <= kinds and all(e["t"] for e in tr)
    steps = [e["event"] for e in tr if e["kind"] == "step"]
    assert "intake" in steps and "done" in steps                     # pipeline step events are in the live trace
    call = next(e for e in tr if e["kind"] == "llm_call")
    detail = client.get(f"/stats/interaction/{call['id']}").json()   # click-through: one LLM call in full
    assert detail["agent"] == call["agent"] and "output" in detail and "prompt_excerpt" in detail
    assert client.get("/stats/interaction/999999").status_code == 404
    lg = client.get("/logs", params={"run": run_id}).json()
    assert lg["lines"] and all(f"[{run_id}]" in ln for ln in lg["lines"])   # server log, stamped with the run id
    assert any("run %s done" % run_id in ln or "done:" in ln for ln in lg["lines"])
    msgs = client.get(f"/runs/{run_id}/messages").json()
    assert msgs and all(m["role"] != "step" for m in msgs)            # the blackboard conversation stays clean

    u = client.get(f"/stats/usage", params={"run": run_id, "by": "agent"}).json()
    assert u["runs"] == 1 and u["total"]["calls"] >= 1
    assert client.get("/stats/usage", params={"by": "bogus"}).status_code == 400
    c = client.get("/stats/communications", params={"run": run_id}).json()
    assert c["messages_per_run"]["runs"] == 1 and c["calls_per_run"]["max"] >= 1
    assert client.get("/runs/nope/summary").status_code == 404
    assert s["configuration"].startswith("4 full system")

    res = client.get("/stats/results")
    if res.status_code == 200:                      # the committed evaluation summary
        body = res.json()
        assert body["stamp"] and {"all", "scientific"} <= set(body) and body["scientific"][0]["per_case"]
    else:
        assert res.status_code == 404

    # the other review configurations are selectable; the single agent's findings come from its file
    with open(flawed_pdf, "rb") as fh:
        r = client.post("/webhook/protocol", headers=HDR, files={"file": ("p.pdf", fh, "application/pdf")},
                        data={"nct_id": "NCT04470427", "config": "single_verified"})
    assert r.status_code == 200 and r.json()["config"] == "single_verified"
    s1 = client.get(f"/runs/{r.json()['run_id']}/summary").json()
    assert s1["status"] == "done" and s1["configuration"].startswith("2 single LLM call") and s1["n_findings"] > 0
    tr1 = client.get(f"/stats/trace/{r.json()['run_id']}").json()
    assert any(e["agent"] == "single_agent" for e in tr1)
    with open(flawed_pdf, "rb") as fh:
        r = client.post("/webhook/protocol", headers=HDR, files={"file": ("p.pdf", fh, "application/pdf")},
                        data={"config": "agents_no_critic", "force_scientific": "true"})
    s3 = client.get(f"/runs/{r.json()['run_id']}/summary").json()
    assert s3["configuration"].startswith("3 full system without")
    with open(flawed_pdf, "rb") as fh:
        r = client.post("/webhook/protocol", headers=HDR, files={"file": ("p.pdf", fh, "application/pdf")}, data={"config": "bogus"})
    assert r.status_code == 400

    # the same protocol (NCT04470427) under several configurations
    cmp_ = client.get(f"/runs/{run_id}/compare").json()
    assert cmp_["protocol"] == "NCT04470427"
    labels = [row["configuration"][:1] for row in cmp_["rows"]]
    assert labels == sorted(labels) and {"4", "2"} <= set(labels)
    assert all(row["llm_calls"] >= 1 and "decision" in row for row in cmp_["rows"])
