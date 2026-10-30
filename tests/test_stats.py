"""`stats`: token usage aggregated from the historical memory."""
from protocol_review import stats
from protocol_review.cli import main
from protocol_review.db import Interaction, Run, get_session


def _seed():
    with get_session() as db:
        db.add(Run(id="st-run-1", source="test", submitter="t", pdf_path="x.pdf", nct_id="", status="done", decision="RETURNED_ADMIN"))
        db.add(Run(id="st-run-2", source="test", submitter="t", pdf_path="y.pdf", nct_id="", status="done", decision="PASS"))
        db.add_all([
            Interaction(run_id="st-run-1", agent="administrative", model="m", input_tokens=100, output_tokens=10, duration_s=1.0, fallback_used=0),
            Interaction(run_id="st-run-1", agent="scientific_reviewer", model="m", input_tokens=300, output_tokens=30, duration_s=3.0, fallback_used=1),
            Interaction(run_id="st-run-2", agent="administrative", model="m", input_tokens=50, output_tokens=5, duration_s=0.5, fallback_used=0),
        ])
        db.commit()


def test_usage_by_agent_and_prefix():
    _seed()
    u = stats.usage("st-run-")
    assert u["runs"] == 2 and u["total"]["calls"] == 3 and u["total"]["input_tokens"] == 450
    by = {r["key"]: r for r in u["rows"]}
    assert by["administrative"]["calls"] == 2 and by["scientific_reviewer"]["fallbacks"] == 1
    assert u["decisions"] == {"RETURNED_ADMIN": 1, "PASS": 1}
    one = stats.usage("st-run-1", by="run")
    assert one["runs"] == 1 and one["rows"][0]["key"] == "st-run-1" and one["total"]["output_tokens"] == 40
    text = stats.format_usage(u)
    assert "per run" in text and "450" in text


def test_cli_stats(capsys):
    _seed()
    assert main(["stats", "--run", "st-run-", "--by", "model"]) == 0
    out = capsys.readouterr().out
    assert "by model" in out and "total" in out
