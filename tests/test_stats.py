"""`stats`: token usage, agent communications and revision rounds aggregated from the memory tables."""
import uuid

from protocol_review import stats
from protocol_review.cli import main
from protocol_review.db import Interaction, Run, RunMessage, get_session


def _seed() -> str:
    p = f"st-{uuid.uuid4().hex[:8]}-"      # unique ids per test: the test database lives for the whole session
    with get_session() as db:
        db.add(Run(id=p + "1", source="test", submitter="t", pdf_path="x.pdf", nct_id="", status="done",
                   decision="RETURNED_ADMIN", state={"revise_rounds": 1}))
        db.add(Run(id=p + "2", source="test", submitter="t", pdf_path="y.pdf", nct_id="", status="done",
                   decision="PASS", state={"revise_rounds": 0}))
        db.add_all([
            Interaction(run_id=p + "1", agent="administrative", model="m", input_tokens=100, output_tokens=10, duration_s=1.0, fallback_used=0),
            Interaction(run_id=p + "1", agent="scientific_reviewer", model="m", input_tokens=300, output_tokens=30, duration_s=3.0, fallback_used=1),
            Interaction(run_id=p + "2", agent="administrative", model="m", input_tokens=50, output_tokens=5, duration_s=0.5, fallback_used=0),
            RunMessage(run_id=p + "1", agent="coordinator", role="system", content="intake"),
            RunMessage(run_id=p + "1", agent="administrative", role="agent", content="done"),
            RunMessage(run_id=p + "1", agent="scientific_reviewer", role="agent", content="round 0"),
            RunMessage(run_id=p + "2", agent="coordinator", role="system", content="intake"),
        ])
        db.commit()
    return p


def test_usage_by_agent_and_prefix():
    p = _seed()
    u = stats.usage(p)
    assert u["runs"] == 2 and u["total"]["calls"] == 3 and u["total"]["input_tokens"] == 450
    by = {r["key"]: r for r in u["rows"]}
    assert by["administrative"]["calls"] == 2 and by["scientific_reviewer"]["fallbacks"] == 1
    assert u["decisions"] == {"RETURNED_ADMIN": 1, "PASS": 1}
    one = stats.usage(p + "1", by="run")
    assert one["runs"] == 1 and one["rows"][0]["key"] == p + "1" and one["total"]["output_tokens"] == 40
    assert "per run" in stats.format_usage(u) and "450" in stats.format_usage(u)


def test_communications_and_revisions():
    p = _seed()
    c = stats.communications(p)
    assert c["messages"]["coordinator"] == {"system": 2} and c["messages"]["administrative"] == {"agent": 1}
    assert c["messages_per_run"] == {"max": 3, "mean": 2.0, "runs": 2}
    assert c["calls_per_run"]["max"] == 2
    assert c["revisions"] == {"max": 1, "mean": 0.5, "runs": 2, "with_revision": 1}
    assert "revision rounds" in stats.format_communications(c)


def test_cli_stats(capsys):
    p = _seed()
    assert main(["stats", "--run", p, "--by", "model"]) == 0
    out = capsys.readouterr().out
    assert "by model" in out and "total" in out and "Agent communications" in out


def test_config_grouping_and_trace(capsys):
    p = _seed()
    assert stats._config_of("abl-agents_full-nct1-20261029") == stats.CONFIG_LABELS["agents_full"]
    assert stats._config_of(p + "1") == "other"
    u = stats.usage(p, by="config")
    assert u["rows"][0]["key"] == "other" and u["rows"][0]["runs"] == 2 and u["rows"][0]["calls"] == 3
    ev = stats.trace(p + "1")
    assert [e["kind"] for e in ev].count("llm_call") == 2 and [e["kind"] for e in ev].count("message") == 3
    assert main(["stats", "--trace", p + "1"]) == 0
    assert "[LLM ]" in capsys.readouterr().out
