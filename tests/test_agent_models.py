"""Optional model per agent (model comparison, mentor M8): the hybrid row uses Opus for the scientific agents and Sonnet
for the coordinator and the administrative agent; by default every agent uses the one configured model."""
import sys
from pathlib import Path
from types import SimpleNamespace

from pydantic import BaseModel

from protocol_review.config import settings
from protocol_review.llm import LLM

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "eval"))
import ablation  # noqa: E402


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


def test_default_is_one_model_for_every_agent():
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
    for agent in ("coordinator", "scientific_reviewer", "administrative", "scientific_critic"):
        llm.structured(agent=agent, system="s", user="u", schema=_Answer)
    assert client.models == ["model-b", "model-a", "model-b", "model-a"]
    assert seen == [("coordinator", "model-b"), ("scientific_reviewer", "model-a"), ("administrative", "model-b"), ("scientific_critic", "model-a")]
    assert llm._active_model == "model-a"                       # back to the default after every call


def test_hybrid_row_is_opt_in_and_names_its_models():
    hybrid = next(c for c in ablation.MODEL_CONFIGS if c["key"] == "agents_full_hybrid")
    assert hybrid["model"] == "claude-opus-5-5"
    assert hybrid["agent_models"] == {"coordinator": "claude-sonnet-5-5", "administrative": "claude-sonnet-5-5"}
    assert "agents_full_hybrid" not in [c["key"] for c in ablation.CONFIGS] and ablation.ROW_NUM["agents_full_hybrid"] == "4-M"
