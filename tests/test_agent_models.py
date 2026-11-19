"""Model per agent (model comparison, mentor M8). Product default since 13 November 2026: Opus for the scientific agents,
Sonnet for the coordinator and the administrative agent (row 4-M of the evaluation). The evaluation runner sets the models
of every row itself, so the default never reaches the single-model rows."""
import sys
from pathlib import Path
from types import SimpleNamespace

from pydantic import BaseModel

from protocol_review.config import Settings, settings
from protocol_review.llm import LLM

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "eval"))
import ablation  # noqa: E402

HYBRID = {"coordinator": "claude-sonnet-5-5", "administrative": "claude-sonnet-5-5"}


class _Answer(BaseModel):
    ok: bool


class _StubClient:
    """Records the model of every request and answers a valid JSON object."""

    def __init__(self):
        self.models = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.models.append(kwargs["model"])
        return SimpleNamespace(content=[SimpleNamespace(type="text", text='{"ok": true}')], stop_reason="end_turn", model=kwargs["model"],
                               usage=SimpleNamespace(input_tokens=1, output_tokens=1, iterations=[]))


def test_product_default_is_the_hybrid_assignment():
    assert Settings.model_fields["llm_agent_models"].default == HYBRID
    assert Settings.model_fields["llm_model"].default == "claude-opus-5-5"


def test_no_agent_models_means_one_model_for_every_agent(monkeypatch):
    monkeypatch.setattr(settings, "llm_agent_models", {})
    client = _StubClient()
    llm = LLM(client=client, model="model-a", fallbacks=False)
    for agent in ("coordinator", "administrative", "scientific_reviewer", "scientific_critic"):
        assert llm.structured(agent=agent, system="s", user="u", schema=_Answer).ok
    assert client.models == ["model-a"] * 4


def test_agent_models_override_only_the_named_agents(monkeypatch):
    monkeypatch.setattr(settings, "llm_agent_models", {"coordinator": "model-b", "administrative": "model-b"})
    client = _StubClient()
    seen = []
    llm = LLM(client=client, model="model-a", fallbacks=False, on_interaction=lambda r, s, u, o: seen.append((r.agent, r.model)))
    for agent in ("coordinator", "scientific_reviewer", "administrative", "scientific_critic", "single_agent"):
        llm.structured(agent=agent, system="s", user="u", schema=_Answer)
    assert client.models == ["model-b", "model-a", "model-b", "model-a", "model-a"]
    assert seen[:2] == [("coordinator", "model-b"), ("scientific_reviewer", "model-a")]
    assert llm._active_model == "model-a"                       # back to the default after every call


def test_hybrid_row_is_opt_in_and_names_its_models():
    hybrid = next(c for c in ablation.MODEL_CONFIGS if c["key"] == "agents_full_hybrid")
    assert hybrid["model"] == "claude-opus-5-5" and hybrid["agent_models"] == HYBRID
    assert "agents_full_hybrid" not in [c["key"] for c in ablation.CONFIGS] and ablation.ROW_NUM["agents_full_hybrid"] == "4-M"


def test_prompt_row_has_the_settings_of_the_hybrid_row():
    """Row 4-MP (prompts of 19 November 2026) differs from row 4-M only by its key and label: same models, same switches."""
    rows = {c["key"]: c for c in ablation.MODEL_CONFIGS}
    a, b = rows["agents_full_hybrid"], rows["agents_full_hybrid_prompt"]
    assert {k: v for k, v in a.items() if k not in ("key", "label")} == {k: v for k, v in b.items() if k not in ("key", "label")}
    assert ablation.ROW_NUM["agents_full_hybrid_prompt"] == "4-MP"


def test_evaluation_rows_do_not_inherit_the_product_default(tmp_path, registry_fetch, monkeypatch):
    """While a single-model row runs, no agent model is set, whatever the product default is; afterwards it is restored."""
    monkeypatch.setattr(settings, "llm_agent_models", dict(HYBRID))
    seen = []
    real = ablation.run_config

    def spy(cfg, cases, **kw):
        seen.append((cfg["key"], dict(settings.llm_agent_models)))
        return real(cfg, cases, **kw)
    monkeypatch.setattr(ablation, "run_config", spy)
    ablation.run_ablation(ROOT / "eval" / "labeled_cases", tmp_path / "results.md", no_llm=True, registry_fetch=registry_fetch,
                          results_dir=tmp_path / "results", pattern="synthetic_*.json", only=["agents_full", "agents_full_hybrid"])
    assert seen == [("agents_full", {}), ("agents_full_hybrid", HYBRID)]
    assert settings.llm_agent_models == HYBRID
