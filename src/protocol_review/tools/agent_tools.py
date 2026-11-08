"""Tools an LLM agent may call itself (v1.7, tool use). Written once; each agent gets a subset.

    search_protocol(query)            pages and snippets where the words of the query occur
    get_page(page) / get_section(name) a page or a section of the protocol JSON, in full (capped)
    registry_field(name)              one field of the ClinicalTrials.gov record
    kb_lookup(code)                   the knowledge-base text of one SPIRIT / GCP / ADMIN-CHK item
    power_calc(...)                   sample size per arm computed by code (two proportions or two means)

The deterministic verification (agents/base.verify_evidence) still runs after the tool loop: a tool call never
replaces it.
"""
from __future__ import annotations

import json
import math
import re
from statistics import NormalDist
from typing import Callable

from ..knowledge_base import load_kb

MAX_RESULT_CHARS = 2000

TOOL_SPECS: dict[str, dict] = {
    "search_protocol": {
        "name": "search_protocol",
        "description": "Search the whole protocol text for words or phrases (case-insensitive). Use it before claiming that "
                       "something is missing, to check whether it is described on another page. Returns up to 8 hits with page "
                       "numbers and short snippets.",
        "input_schema": {"type": "object", "properties": {"query": {"type": "string", "description": "one or more words or a short phrase; separate alternatives with |"}},
                         "required": ["query"], "additionalProperties": False},
    },
    "get_page": {
        "name": "get_page",
        "description": "Return the text of one protocol page (1-based), to read the context around a quote.",
        "input_schema": {"type": "object", "properties": {"page": {"type": "integer", "minimum": 1}, "offset": {"type": "integer", "minimum": 0, "description": "character offset when the page is longer than the cap"}},
                         "required": ["page"], "additionalProperties": False},
    },
    "get_section": {
        "name": "get_section",
        "description": "Return the text of one protocol section by (part of) its heading, e.g. 'sample size' or '9.2'.",
        "input_schema": {"type": "object", "properties": {"name": {"type": "string"}, "offset": {"type": "integer", "minimum": 0}},
                         "required": ["name"], "additionalProperties": False},
    },
    "registry_field": {
        "name": "registry_field",
        "description": "Return one field of the ClinicalTrials.gov record of this trial: title, phase, status, enrollment, "
                       "conditions, interventions, primary_outcomes, sponsor, or 'all'.",
        "input_schema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"], "additionalProperties": False},
    },
    "kb_lookup": {
        "name": "kb_lookup",
        "description": "Return the knowledge-base text of one guideline item, e.g. 'SPIRIT-27b', 'GCP-07' or 'ADMIN-CHK-06', "
                       "to check that the item really requires what a finding claims.",
        "input_schema": {"type": "object", "properties": {"code": {"type": "string"}}, "required": ["code"], "additionalProperties": False},
    },
    "power_calc": {
        "name": "power_calc",
        "description": "Compute the sample size per arm in code (never do this arithmetic yourself). Two proportions: give p1 and p2. "
                       "Two means: give mean_diff and sd. alpha (two-sided) defaults to 0.05, power to 0.8, dropout to 0.",
        "input_schema": {"type": "object", "properties": {
            "p1": {"type": "number"}, "p2": {"type": "number"}, "mean_diff": {"type": "number"}, "sd": {"type": "number"},
            "alpha": {"type": "number"}, "power": {"type": "number"}, "dropout": {"type": "number", "description": "expected dropout fraction, e.g. 0.1"},
            "allocation_ratio": {"type": "number", "description": "n2/n1, default 1"}}, "additionalProperties": False},
    },
}
REVIEWER_TOOLS = ["search_protocol", "get_page", "get_section", "kb_lookup", "power_calc"]
CRITIC_TOOLS = ["search_protocol", "get_page", "get_section", "registry_field", "kb_lookup"]
SINGLE_AGENT_TOOLS = ["search_protocol", "get_page", "get_section", "registry_field", "kb_lookup", "power_calc"]


def specs(names: list[str]) -> list[dict]:
    return [TOOL_SPECS[n] for n in names]


def _cap(s: str, offset: int = 0) -> str:
    s = s[offset:]
    if len(s) > MAX_RESULT_CHARS:
        return s[:MAX_RESULT_CHARS] + f"\n[... {len(s) - MAX_RESULT_CHARS} more characters; call again with offset={offset + MAX_RESULT_CHARS}]"
    return s


def power_calc(p1=None, p2=None, mean_diff=None, sd=None, alpha=0.05, power=0.8, dropout=0.0, allocation_ratio=1.0) -> dict:
    """Normal-approximation sample size per arm (two-sided alpha)."""
    z_a = NormalDist().inv_cdf(1 - alpha / 2)
    z_b = NormalDist().inv_cdf(power)
    k = allocation_ratio or 1.0
    if p1 is not None and p2 is not None:
        if not (0 < p1 < 1 and 0 < p2 < 1) or p1 == p2:
            return {"error": "p1 and p2 must be proportions in (0,1) and different"}
        pbar = (p1 + k * p2) / (1 + k)
        n1 = ((z_a * math.sqrt((1 + 1 / k) * pbar * (1 - pbar)) + z_b * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2) / k)) ** 2) / (p1 - p2) ** 2
        kind = "two proportions"
    elif mean_diff is not None and sd:
        if mean_diff == 0:
            return {"error": "mean_diff must be non-zero"}
        n1 = (1 + 1 / k) * (sd ** 2) * (z_a + z_b) ** 2 / mean_diff ** 2
        kind = "two means"
    else:
        return {"error": "give p1 and p2, or mean_diff and sd"}
    n1 = math.ceil(n1); n2 = math.ceil(n1 * k)
    infl = 1 / (1 - dropout) if 0 <= dropout < 1 else 1.0
    return {"test": kind, "alpha_two_sided": alpha, "power": power, "n_per_arm": n1, "n_arm2": n2, "n_total": n1 + n2,
            "n_total_with_dropout": math.ceil((n1 + n2) * infl), "dropout": dropout,
            "formula": "normal approximation; compare with the protocol's own figure and assumptions"}


def make_executor(pages: list[dict], protocol_json: dict | None, registry: dict | None) -> Callable[[str, dict], str]:
    """Bind the tools to one run's data. Every result is a string capped at MAX_RESULT_CHARS."""
    by_page = {p["page"]: p["text"] for p in pages}
    sections = (protocol_json or {}).get("sections") or []
    kb = load_kb()

    def search_protocol(query: str) -> str:
        terms = [t.strip() for t in re.split(r"\s*\|\s*", query or "") if t.strip()] or [query]
        hits = []
        for t in terms:
            rx = re.compile(re.escape(t), re.I)
            for p in pages:
                for m in rx.finditer(p["text"]):
                    s = max(0, m.start() - 100); e = min(len(p["text"]), m.end() + 100)
                    hits.append(f"p.{p['page']} [{t}]: ..." + " ".join(p["text"][s:e].split()) + "...")
                    if len(hits) >= 8:
                        break
                if len(hits) >= 8:
                    break
        if not hits:
            return f"no occurrence of {terms} anywhere in the {len(pages)} pages"
        return f"{len(hits)} hit(s) (max 8 shown):\n" + "\n".join(hits)

    def get_page(page: int, offset: int = 0) -> str:
        if page not in by_page:
            return f"page {page} does not exist (the protocol has {len(pages)} pages)"
        return _cap(f"=== PAGE {page} ===\n" + by_page[page], offset)

    def get_section(name: str, offset: int = 0) -> str:
        q = (name or "").lower().strip()
        hit = next((s for s in sections if q and (q in (s.get("title") or "").lower() or q == str(s.get("number") or "").lower())), None)
        if hit is None:
            cands = ", ".join(f"{s.get('number') or ''} {s.get('title') or ''}".strip() for s in sections[:40])
            return f"no section matching '{name}'. Sections: {cands}"
        return _cap(f"=== SECTION {hit.get('number') or ''} {hit.get('title') or ''} (pages {hit.get('page_start')}-{hit.get('page_end')}) ===\n{hit.get('text') or ''}", offset)

    def registry_field(name: str) -> str:
        if not registry or not registry.get("found"):
            return "ClinicalTrials.gov record not available for this run" + (f" ({registry.get('error')})" if registry else "")
        fields = {k: registry.get(k) for k in ("nct_id", "title", "phase", "status", "enrollment", "conditions", "interventions", "primary_outcomes", "sponsor")}
        if (name or "all").lower() == "all":
            return _cap(json.dumps(fields, indent=1, ensure_ascii=False))
        key = name.lower().strip()
        if key not in fields:
            return f"unknown field '{name}'. Fields: {', '.join(fields)}"
        return json.dumps({key: fields[key]}, ensure_ascii=False)

    def kb_lookup(code: str) -> str:
        c = (code or "").strip()
        m = re.match(r"(ADMIN-CHK-\d{2}|SPIRIT-\d{1,2}[a-dA-D]?|GCP-\d{2})", c, re.I)
        if not m:
            return f"'{code}' is not a knowledge-base code (expected SPIRIT-nn[a-d], GCP-nn or ADMIN-CHK-nn)"
        c = m.group(1)
        c = c[:-1] + c[-1].lower() if c[-1].isalpha() else c
        out = []
        for d in kb:
            for para in re.split(r"\n\s*\n", d.text):
                if re.search(rf"\b{re.escape(c)}\b", para) or re.search(rf"\|\s*{re.escape(c)}\s*\|", para):
                    lines = [ln for ln in para.splitlines() if re.search(rf"\b{re.escape(c)}\b", ln)] or [para]
                    out.append(f"[{d.domain}/{d.name}] " + " ".join(" ".join(lines).split())[:600])
        return _cap("\n".join(out)) if out else f"{c} is not defined in the knowledge base (do not cite it)"

    def run(name: str, args: dict) -> str:
        try:
            if name == "search_protocol":
                return search_protocol(**args)
            if name == "get_page":
                return get_page(**args)
            if name == "get_section":
                return get_section(**args)
            if name == "registry_field":
                return registry_field(**args)
            if name == "kb_lookup":
                return kb_lookup(**args)
            if name == "power_calc":
                return json.dumps(power_calc(**args))
            return f"unknown tool {name}"
        except TypeError as exc:
            return f"bad arguments for {name}: {exc}"
        except Exception as exc:  # a tool error must never break the review
            return f"tool {name} failed: {exc}"

    return run
