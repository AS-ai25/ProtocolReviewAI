from fastapi.testclient import TestClient

from protocol_review import memory
from protocol_review.api import app
from protocol_review.llm import LLMResult, strict_schema
from protocol_review.state import AdminReport, CriticReport, ScientificReport

HDR = {"X-Webhook-Secret": "test-secret"}


def test_memory_layers_roundtrip():
    mid = memory.propose_memory("scientific_reviewer", "Sponsor X protocols often omit DSMB charters.", scope="sponsor",
                                scope_ref="Helix", run_id="r1", proposed_by="scientific_critic")
    assert mid > 0
    assert memory.propose_memory("scientific_reviewer", "Sponsor X protocols often omit DSMB charters.", scope="sponsor", scope_ref="Helix") == mid
    assert memory.recall_memories("scientific_reviewer", {"sponsor": "Helix Biologics"}) == []
    memory.decide_memory(mid, True, "coordinator@example.org", edited_fact="Helix protocols often omit DSMB charters.")
    got = memory.recall_memories("scientific_reviewer", {"sponsor": "Helix Biologics"})
    assert got and got[0]["fact"].startswith("Helix")
    assert memory.recall_memories("scientific_reviewer", {"sponsor": "Other"}) == []
    assert "Approved lessons" in memory.memories_block("scientific_reviewer", {"sponsor": "Helix"})
    assert memory.deactivate_memory(mid, "admin")
    assert memory.recall_memories("scientific_reviewer", {"sponsor": "Helix"}) == []

    memory.record_interaction("r1", LLMResult(agent="administrative", model="m", input_tokens=10, output_tokens=5, duration_s=1.5), "sys", "usr", {"a": 1})
    cost = memory.run_cost_summary("r1")
    assert cost["llm_calls"] == 1 and cost["input_tokens"] == 10 and cost["by_agent"] == {"administrative": 1}


def test_strict_schema_is_structured_output_compatible():
    for model in (AdminReport, ScientificReport, CriticReport):
        s = strict_schema(model)
        assert s["additionalProperties"] is False
        assert set(s["required"]) == set(s["properties"])
        text = str(s)
        assert "'default'" not in text
        for d in s.get("$defs", {}).values():
            if d.get("type") == "object":
                assert d["additionalProperties"] is False


def test_api_flow(flawed_pdf):
    client = TestClient(app)
    assert client.get("/health").json()["status"] == "ok"
    with open(flawed_pdf, "rb") as fh:
        r = client.post("/webhook/protocol", files={"file": ("p.pdf", fh, "application/pdf")})
    assert r.status_code == 401
    with open(flawed_pdf, "rb") as fh:
        r = client.post("/webhook/protocol", headers=HDR, files={"file": ("p.pdf", fh, "application/pdf")},
                        data={"submitter": "ron@example.org", "nct_id": "NCT04368728"})
    assert r.status_code == 200, r.text
    run_id = r.json()["run_id"]
    run = client.get(f"/runs/{run_id}").json()        # background task completed inside TestClient
    assert run["status"] == "done" and run["decision"] == "RETURNED_ADMIN"
    assert client.get(f"/runs/{run_id}/report").status_code == 200
    assert client.get(f"/runs/{run_id}/report?kind=scientific").status_code == 404
    assert any(m["agent"] == "administrative" for m in client.get(f"/runs/{run_id}/messages").json())
    assert client.get("/runs").json()[0]["id"] == run_id

    r = client.post("/webhook/protocol", headers=HDR, files={"file": ("x.pdf", b"not a pdf", "application/pdf")})
    assert r.status_code == 400

    mid = memory.propose_memory("administrative", "Always check appendix list vs attachments.")
    assert any(m["id"] == mid for m in client.get("/memory", headers=HDR).json())
    r = client.post(f"/memory/{mid}/approve", headers=HDR, json={"decided_by": "coordinator"})
    assert r.json()["status"] == "approved"
    assert all(m["id"] != mid for m in client.get("/memory?status=proposed", headers=HDR).json())


def test_baseline_endpoint(good_pdf):
    client = TestClient(app)
    with open(good_pdf, "rb") as fh:
        r = client.post("/baseline", headers=HDR, files={"file": ("good.pdf", fh, "application/pdf")})
    assert r.status_code == 200
    assert r.json()["mode"] == "rule_based_baseline"
