"""Thin wrapper around the Anthropic SDK for structured (JSON-schema) agent calls.

* Uses `client.beta.messages.create` with `output_config.format = json_schema`
  so each agent returns a validated pydantic object.
* Opts into server-side refusal fallbacks (`fallbacks: "default"`) on the Claude
  API; disable with LLM_FALLBACKS=false on Bedrock / Vertex.
* Handles `stop_reason == "refusal"` explicitly.
* `MockLLM` lets the whole graph run in tests / NO_LLM mode without network.
"""
from __future__ import annotations

from contextlib import contextmanager

import json
import logging
import time
from typing import Any, Callable, TypeVar

import anthropic
from pydantic import BaseModel, ValidationError

from .config import settings

log = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)

FALLBACK_BETA = "server-side-fallback-2026-07-01"


class LLMError(RuntimeError):
    pass


class LLMRefusal(LLMError):
    pass


def strict_schema(model: type[BaseModel]) -> dict:
    """Pydantic schema -> structured-outputs-compatible schema.

    Every object gets `additionalProperties: false` and all its properties
    become required; `default` keys are dropped (the API rejects them).
    """
    schema = model.model_json_schema()

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            node.pop("default", None)
            if node.get("type") == "object" and "properties" in node:
                node["additionalProperties"] = False
                node["required"] = list(node["properties"].keys())
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(schema)
    return schema


class LLMResult(BaseModel):
    agent: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    duration_s: float = 0.0
    fallback_used: bool = False
    raw_text: str = ""
    tool_calls: list[dict] = []          # v1.7: tools the model called itself (name, input, result size, duration)


class LLM:
    """Structured-output client. `on_interaction` receives (LLMResult, system, user, parsed_dict)."""

    def __init__(
        self,
        client: anthropic.Anthropic | None = None,
        model: str | None = None,
        effort: str | None = None,
        max_tokens: int | None = None,
        fallbacks: bool | None = None,
        on_interaction: Callable[[LLMResult, str, str, dict], None] | None = None,
    ):
        self.client = client or anthropic.Anthropic(api_key=settings.anthropic_api_key or None)
        self.model = model or settings.llm_model
        self.agent_models = dict(settings.llm_agent_models or {})     # optional model per agent; others use self.model
        self._active_model = self.model
        self.effort = effort or settings.llm_effort
        self.max_tokens = max_tokens or settings.llm_max_tokens
        self.fallbacks = settings.llm_fallbacks if fallbacks is None else fallbacks
        self.on_interaction = on_interaction

    # ------------------------------------------------------------------ public
    @contextmanager
    def _for_agent(self, agent: str):
        """The model of this call: the agent's own model when one is configured, else the default."""
        previous = self._active_model
        self._active_model = self.agent_models.get(agent) or self.model
        try:
            yield
        finally:
            self._active_model = previous

    def structured(self, *, agent: str, system: str, user: str, schema: type[T]) -> T:
        with self._for_agent(agent):
            return self._structured(agent=agent, system=system, user=user, schema=schema)

    def structured_with_tools(self, *, agent: str, system: str, user: str, schema: type[T], tools: list[dict],
                              executor: Callable[[str, dict], str], max_tool_calls: int = 6) -> T:
        with self._for_agent(agent):
            return self._structured_with_tools(agent=agent, system=system, user=user, schema=schema, tools=tools,
                                               executor=executor, max_tool_calls=max_tool_calls)

    def _structured(self, *, agent: str, system: str, user: str, schema: type[T]) -> T:
        """One request -> validated `schema` instance. One repair retry on bad JSON."""
        started = time.perf_counter()
        text, usage, fallback_used, model_used = self._call(system, user, schema, use_format=True)
        try:
            obj = self._parse(text, schema)
        except (ValidationError, json.JSONDecodeError) as exc:
            log.warning("[%s] invalid structured output, retrying once: %s", agent, exc)
            repair = (
                f"{user}\n\nYour previous answer was not valid for the required schema "
                f"({type(exc).__name__}: {str(exc)[:500]}). Return ONLY a corrected JSON object."
            )
            text, usage2, fb2, model_used = self._call(system, repair, schema, use_format=True)
            usage = {k: usage.get(k, 0) + usage2.get(k, 0) for k in ("input_tokens", "output_tokens")}
            fallback_used = fallback_used or fb2
            obj = self._parse(text, schema)
        result = LLMResult(
            agent=agent,
            model=model_used,
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            duration_s=round(time.perf_counter() - started, 2),
            fallback_used=fallback_used,
            raw_text=text,
        )
        log.info("[%s] %s in=%d out=%d %.1fs%s", agent, model_used, result.input_tokens, result.output_tokens,
                 result.duration_s, " FALLBACK" if fallback_used else "")
        if self.on_interaction:
            try:
                self.on_interaction(result, system, user, obj.model_dump(mode="json"))
            except Exception:  # never let bookkeeping break the pipeline
                log.exception("on_interaction hook failed")
        return obj

    def _structured_with_tools(self, *, agent: str, system: str, user: str, schema: type[T], tools: list[dict],
                              executor: Callable[[str, dict], str], max_tool_calls: int = 6) -> T:
        """v1.7 tool use: the model may call the given tools (it decides which and when, up to `max_tool_calls`);
        the code executes them and feeds the results back; then one final request without tools returns the
        validated `schema`. Token usage of every request is summed into one LLMResult; the calls are kept in
        `tool_calls` and reach the historical memory and the dashboard."""
        started = time.perf_counter()
        messages: list[dict] = [{"role": "user", "content": user}]
        usage = {"input_tokens": 0, "output_tokens": 0}
        calls: list[dict] = []
        fallback_used = False
        model_used = self.model
        for _ in range(max_tool_calls + 1):
            response = self._create(system, messages, schema, use_format=False, tools=tools)
            usage = {k: usage[k] + (getattr(response.usage, k, 0) or 0) for k in usage}
            model_used = getattr(response, "model", self.model)
            tool_uses = [b for b in response.content if getattr(b, "type", "") == "tool_use"]
            if not tool_uses or len(calls) >= max_tool_calls:
                break
            messages.append({"role": "assistant", "content": [self._block(b) for b in response.content]})
            results = []
            for tu in tool_uses:
                args = dict(getattr(tu, "input", None) or {})
                t0 = time.perf_counter()
                out = executor(tu.name, args)
                calls.append({"tool": tu.name, "input": args, "result_chars": len(out), "duration_s": round(time.perf_counter() - t0, 3),
                              "result_preview": out[:300]})
                results.append({"type": "tool_result", "tool_use_id": tu.id, "content": out})
            messages.append({"role": "user", "content": results})
        messages.append({"role": "user", "content": f"Now return the {schema.__name__} JSON, using what the tools showed you. "
                                                    "Do not call any more tools."})
        text, usage2, fb2, model_used = self._call_messages(system, messages, schema, use_format=True)
        usage = {k: usage[k] + usage2.get(k, 0) for k in usage}
        try:
            obj = self._parse(text, schema)
        except (ValidationError, json.JSONDecodeError) as exc:
            log.warning("[%s] invalid structured output after tools, retrying once: %s", agent, exc)
            messages.append({"role": "assistant", "content": text})
            messages.append({"role": "user", "content": f"Your answer was not valid for the required schema ({type(exc).__name__}: "
                                                        f"{str(exc)[:500]}). Return ONLY a corrected JSON object."})
            text, usage3, fb3, model_used = self._call_messages(system, messages, schema, use_format=True)
            usage = {k: usage[k] + usage3.get(k, 0) for k in usage}
            fb2 = fb2 or fb3
            obj = self._parse(text, schema)
        result = LLMResult(agent=agent, model=model_used, input_tokens=usage["input_tokens"], output_tokens=usage["output_tokens"],
                           duration_s=round(time.perf_counter() - started, 2), fallback_used=fallback_used or fb2, raw_text=text,
                           tool_calls=calls)
        log.info("[%s] %s in=%d out=%d %.1fs tools=%d%s", agent, model_used, result.input_tokens, result.output_tokens,
                 result.duration_s, len(calls), " FALLBACK" if result.fallback_used else "")
        if self.on_interaction:
            try:
                self.on_interaction(result, system, user, obj.model_dump(mode="json"))
            except Exception:
                log.exception("on_interaction hook failed")
        return obj

    @staticmethod
    def _block(b) -> dict:
        """SDK content block -> plain dict for the next request. Thinking blocks (with their signature) must be passed
        back unchanged when the model thinks before calling a tool, so the whole block is kept."""
        if hasattr(b, "model_dump"):
            return b.model_dump(exclude_none=True)
        return dict(b)

    # ----------------------------------------------------------------- private
    def _request_kwargs(self, system: str, messages: list[dict], schema: type[BaseModel], use_format: bool,
                        tools: list[dict] | None = None) -> dict:
        kwargs: dict[str, Any] = dict(
            model=self._active_model,
            max_tokens=self.max_tokens,
            system=system,
            messages=messages,
            output_config={"effort": self.effort},
        )
        if use_format:
            kwargs["output_config"]["format"] = {"type": "json_schema", "schema": strict_schema(schema)}
        if tools:
            kwargs["tools"] = tools
        if self.fallbacks:
            kwargs["betas"] = [FALLBACK_BETA]
            kwargs["extra_body"] = {"fallbacks": "default"}
        return kwargs

    def _create(self, system: str, messages: list[dict], schema: type[BaseModel], use_format: bool, tools: list[dict] | None = None):
        """One API request with the error mapping; returns the raw response."""
        kwargs = self._request_kwargs(system, messages, schema, use_format, tools)
        try:
            response = self.client.beta.messages.create(**kwargs)
        except anthropic.BadRequestError as exc:
            raise LLMError(f"Bad request: {exc}") from exc
        except anthropic.RateLimitError as exc:
            raise LLMError("Rate limited by the Claude API; retry later") from exc
        except anthropic.APIStatusError as exc:
            raise LLMError(f"Claude API error {exc.status_code}: {exc.message}") from exc
        except anthropic.APIConnectionError as exc:
            raise LLMError("Could not reach the Claude API") from exc
        if response.stop_reason == "refusal":
            details = getattr(response, "stop_details", None)
            raise LLMRefusal(f"Model declined the request ({getattr(details, 'category', None)})")
        if response.stop_reason == "max_tokens":
            log.warning("response truncated at max_tokens=%s", self.max_tokens)
        return response

    def _call(self, system: str, user: str, schema: type[BaseModel], use_format: bool) -> tuple[str, dict, bool, str]:
        return self._call_messages(system, [{"role": "user", "content": user}], schema, use_format)

    def _call_messages(self, system: str, messages: list[dict], schema: type[BaseModel], use_format: bool) -> tuple[str, dict, bool, str]:
        try:
            response = self._create(system, messages, schema, use_format)
        except LLMError as exc:
            msg = str(exc)
            if use_format and ("schema" in msg.lower() or "output_config" in msg.lower() or "format" in msg.lower()):
                # Schema not accepted -> fall back to prompt-instructed JSON on the last user message
                log.warning("structured format rejected (%s); retrying with prompt-only JSON", msg[:200])
                messages = list(messages)
                last = messages[-1]
                if isinstance(last.get("content"), str):
                    messages[-1] = {"role": "user", "content": last["content"] + "\n\nRespond ONLY with a JSON object matching this JSON schema:\n" + json.dumps(strict_schema(schema))}
                else:
                    messages.append({"role": "user", "content": "Respond ONLY with a JSON object matching this JSON schema:\n" + json.dumps(strict_schema(schema))})
                return self._call_messages(system, messages, schema, use_format=False)
            raise
        text = "".join(getattr(b, "text", "") for b in response.content if getattr(b, "type", "") == "text")
        usage = {
            "input_tokens": getattr(response.usage, "input_tokens", 0) or 0,
            "output_tokens": getattr(response.usage, "output_tokens", 0) or 0,
        }
        iterations = getattr(response.usage, "iterations", None) or []
        fallback_used = any(getattr(it, "type", "") == "fallback_message" for it in iterations)
        return text, usage, fallback_used, getattr(response, "model", self.model)

    @staticmethod
    def _parse(text: str, schema: type[T]) -> T:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            cleaned = cleaned[cleaned.find("{"):]
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start != -1 and end != -1:
            cleaned = cleaned[start:end + 1]
        return schema.model_validate_json(cleaned)


class MockLLM:
    """Deterministic stand-in: `responses[SchemaName]` is a dict, a model, or a callable(system, user)."""

    def __init__(self, responses: dict[str, Any] | None = None, on_interaction=None):
        self.responses = responses or {}
        self.calls: list[dict] = []
        self.model = "mock"
        self.on_interaction = on_interaction

    def structured(self, *, agent: str, system: str, user: str, schema: type[T]) -> T:
        self.calls.append({"agent": agent, "schema": schema.__name__, "user": user})
        payload = self.responses.get(schema.__name__)
        if payload is None:
            raise LLMError(f"MockLLM has no response for {schema.__name__}")
        if callable(payload):
            payload = payload(system, user)
        obj = payload if isinstance(payload, schema) else schema.model_validate(payload)
        if self.on_interaction:
            self.on_interaction(
                LLMResult(agent=agent, model="mock"), system, user, obj.model_dump(mode="json")
            )
        return obj

    def structured_with_tools(self, *, agent: str, system: str, user: str, schema: type[T], tools: list[dict],
                              executor, max_tool_calls: int = 6) -> T:
        """Scripted tool use for tests: `responses["<Schema>__tool_calls"] = [{"name": ..., "input": {...}}, ...]`
        runs those tools through the real executor, then returns the canned response for the schema."""
        script = list(self.responses.get(schema.__name__ + "__tool_calls") or [])[:max_tool_calls]
        calls = []
        for tc in script:
            out = executor(tc["name"], dict(tc.get("input") or {}))
            calls.append({"tool": tc["name"], "input": dict(tc.get("input") or {}), "result_chars": len(out), "duration_s": 0.0,
                          "result_preview": out[:300]})
        self.calls.append({"agent": agent, "schema": schema.__name__, "user": user, "tool_calls": calls})
        payload = self.responses.get(schema.__name__)
        if payload is None:
            raise LLMError(f"MockLLM has no response for {schema.__name__}")
        if callable(payload):
            payload = payload(system, user)
        obj = payload if isinstance(payload, schema) else schema.model_validate(payload)
        if self.on_interaction:
            self.on_interaction(LLMResult(agent=agent, model="mock", tool_calls=calls), system, user, obj.model_dump(mode="json"))
        return obj


def make_llm(on_interaction=None, no_llm: bool | None = None):
    """Factory honouring NO_LLM (returns a MockLLM that yields empty reports)."""
    from .agents.mock_responses import NO_LLM_RESPONSES  # local import avoids cycles

    if settings.no_llm if no_llm is None else no_llm:
        return MockLLM(NO_LLM_RESPONSES, on_interaction=on_interaction)
    return LLM(on_interaction=on_interaction)
