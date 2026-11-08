"""Canned responses for NO_LLM mode (rule-based pipeline through the same graph)."""

NO_LLM_RESPONSES = {
    "AdminReport": {
        "accepted": True,
        "summary": "NO_LLM mode: administrative decision taken from deterministic checks only.",
        "findings": [],
        "checklist": [],
    },
    "ScientificReport": {
        "summary": "NO_LLM mode: scientific findings limited to deterministic checks and registry comparison.",
        "findings": [],
        "registry_comparison": [],
        "open_questions": [],
    },
    "CriticReport": {"summary": "NO_LLM mode: nothing to audit.", "verdicts": [], "missed_issues": [], "proposed_memory": []},
    "SingleAgentReport": {
        "admin_accepted": True,
        "admin_summary": "NO_LLM mode: administrative decision taken from deterministic checks only.",
        "scientific_summary": "NO_LLM mode: scientific findings limited to deterministic checks and registry comparison.",
        "findings": [],
        "checklist": [],
        "registry_comparison": [],
        "open_questions": [],
        "executive_summary": "NO_LLM mode: see the deterministic findings table.",
        "recommendation": "Run with an LLM for the single LLM call baseline.",
    },
    "FinalSummary": {
        "executive_summary": "NO_LLM mode: see the deterministic findings table.",
        "key_findings": [],
        "recommendation": "Run with an LLM for the full multi-agent review.",
    },
}
