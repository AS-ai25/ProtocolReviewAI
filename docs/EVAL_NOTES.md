# Evaluation notes - first live comparison (2026-10-16)

Development numbers on the two **synthetic** cases, Claude Opus 5.5, effort `medium`.
They are **not** the project's evaluation results: the labeled set only contains the
ten deficiencies that were deliberately injected, so every additional (often correct)
observation an LLM makes about a two-page synthetic protocol counts as a false positive.

## Numbers

| Mode | Case | P | R | F1 | Findings | LLM calls | Tokens in / out | Runtime |
|---|---|---|---|---|---|---|---|---|
| Rule-based baseline | flawed | 1.00 | 1.00 | 1.00 | 11 | 0 | 0 | 1 s |
| Rule-based baseline | good | 1.00 | 1.00 | 1.00 | 0 | 0 | 0 | 1 s |
| Single agent | flawed | 0.48 | 1.00 | 0.65 | 25 | 1 | 12.6k / 9.4k | 83 s |
| Single agent | good | 0.00 | 1.00 | 0.00 | 8 | 1 | 10.8k / 6.7k | 55 s |
| Multi-agent (4) | flawed | 0.40* | 0.40* | 0.40* | 14 | 2 | 12.1k / 6.4k | 64 s |
| Multi-agent (4) | good | 0.00 | 1.00 | 0.00 | 32 | 6 | 78.3k / 33.2k | 349 s |

\* Measured **before** commit "include deterministic scientific findings on the
RETURNED_ADMIN path". The flawed protocol is returned at the administrative stage, so
the scientific agents never run (by design); the six "missed" labels were the scientific
*rule* findings, which the single-agent path reported and the multi-agent path dropped.
After the fix the multi-agent flawed case scores the same recall as the single agent
(`--no-llm` check: F1 1.00 on both cases).

## What the numbers do and do not say

- **Recall of injected deficiencies**: both LLM modes find all ten (the deterministic
  checks already do). The synthetic set cannot separate them.
- **Precision** is meaningless here: the "extra" findings (no GDPR basis for the Spanish
  sites, no Spanish consent form, no case definition, NCT id belongs to a different trial)
  are real problems of the synthetic protocol that were never labeled. The CP2 labeled
  set must label *all* defensible findings, including those only an LLM can see.
- **Cost / latency**: single agent ~20k tokens and ~1 min per protocol; multi-agent
  ~110k tokens and ~6 min when the scientific stage runs (admin agent + reviewer +
  critic + one revision round + coordinator summary). Roughly 5x the cost for the
  verification layer.
- **What the multi-agent system adds that the metric does not capture**: every LLM
  finding carries a critic verdict. On the "good" case, 23 of 32 findings were
  `verified` by the critic and 9 were `unverified` (sent to a human); the single agent
  only has the code-level quote check (12 verified / 2 unverified on flawed, 8 / 0 on good)
  and no second opinion, no revision round, and no "missed issues" pass.

## Metric design issues to fix before CP2 (Ron + Amir)

1. Match findings on **meaning**, not on `(domain, category)` string equality: the LLM
   uses the generic categories (CONSENT_GAP, MISSING_DOCUMENT) while the rules use
   specific ones (MISSING_CONSENT_FORM). Options: a category alias map, or matching on
   `guideline_ref` + page, or an LLM judge against the labeled description.
2. Score **verified-only** findings as the system's claims; count `unverified` ones
   separately (they are routed to a human, not asserted).
3. Add the **critic-contribution** metric from the charter: how many reviewer findings
   the critic rejected or downgraded, and how many of those were indeed wrong.
4. Use real public protocols (10-15) with a labeled finding set that includes
   LLM-level findings and documented "no deficiency" items.
