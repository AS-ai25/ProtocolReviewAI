# Checkpoint 2 - evaluation on real protocols: what the numbers say

Companion to `reports/results.md` (generated) - this file is the team's reading of the run of 29 October 2026
(`eval/results/ablation-20261029-205913.json`, model `claude-opus-5-5`, five blind-labeled public protocols,
46 labels, all four ablation rows with the gate bypass). Re-scored views are produced by `eval/rescore.py` from
the saved findings; the LLM outputs were produced once. The tables below are the re-score of 30 October after the
labeler's domain correction (section 2.3); the raw table of the live run, scored with the labels as first delivered,
is kept in `eval/results/results_live_raw_20261029-205913.md`.

## 1. Headline numbers

| View | Row | Precision of verified | Recall of labels | Unverified | Tokens in | Runtime |
|---|---|---|---|---|---|---|
| charter (all domains) | 2 Single agent + verification (baseline) | 13% (13/102) | 46% (21/46) | 21 | 207k | 568 s |
| charter (all domains) | 4 Full system | 23% (43/184) | 74% (34/46) | 51 | 1,280k | 2,372 s |
| scientific only (37 labels) | 2 Single agent + verification (baseline) | 18% (9/50) | 46% (17/37) | 18 | - | - |
| scientific only (37 labels) | 4 Full system | **34% (38/112)** | **78% (29/37)** | 50 | - | - |

Against the charter targets:

* **Recall of labeled findings >= 0.80: narrowly missed** on the scientific view (78%, 29 of 37; one more match would
  reach it); 74% on the all-domain view. The eight misses are all generic `OTHER` labels (section 3).
* **Precision of verified findings >= 0.80: not met** (23% / 34%). See section 2 for why this number is a lower bound
  and what the 30-finding human check adds.
* **+5 pp precision over the Single-Agent Baseline at equal or better recall: met** (+10 pp all-domain, +16 pp scientific;
  recall +28 pp / +32 pp).
* **Cost:** the full system uses ~6x the input tokens and ~4x the runtime of the single agent per protocol.

## 2. Why precision is low, and what it does and does not mean

1. **The system reports far more than the labeler recorded.** Ron labeled about 9 findings per protocol, restricted by
   design to objective, text-verifiable issues. The full system verifies about 37 per protocol. Every verified finding
   that matches no label counts as a false positive, whether it is wrong or merely unlabeled. On the synthetic cases
   (16 October) the same effect appeared: most "extra" findings were real but unlabeled. Precision against the labels
   is therefore a **lower bound** on the true precision; the **30-finding human check** (`eval/human_check/`) measures
   the complement - does the cited passage support the finding - and is the number to read next to it.
2. **Administrative package completeness.** Public registry protocols have no consent form, insurance statement,
   signature page or sponsor declaration. The rules and the administrative agent correctly report those absences
   (verified by construction) and the labeler, by the reduced-scope plan, did not label them: 28 of the 72 verified
   administrative findings are of this kind (consent, insurance, signature page, sponsor, ethics statement, referenced
   documents). The scientific-only view removes this artefact.
3. **Domain classification of 16 labels (corrected 30 October).** Sixteen labels on data management, monitoring,
   amendments, confidentiality and the consent process (SPIRIT-26/29/31/32/33) were first recorded as *administrative*;
   the system raises the same issues through the scientific reviewer (e.g. INVEST: `SCI-L015` "Monitoring plan and
   amendment communication lack detail", SPIRIT-29/31, page 27, is label #1 + #3 of that protocol), so under the
   domain-first rule they could not match. The labeler agreed in writing to move the domain of those 16 findings to
   *scientific* - the domain field only; text, quote, category, severity and page untouched, the original value kept
   in `domain_original`, the untouched files in commit `545a516`. The decision was taken before the labeler saw any
   system output; the tables were rebuilt with `eval/rescore.py` (no new LLM calls). Effect on the full system:
   all-domain recall 61% -> 74%, scientific recall 90% (19/21) -> 78% (29/37) because the scientific label set grew
   from 21 to 37 and the system missed 8 of the 16 moved labels' neighbours. The `expected_decision` stays
   RETURNED_ADMIN for every protocol: the decision is the production rule applied to the real document (which lacks
   consent, insurance and signature documents), not a function of the labels.
4. **Generic-category labels.** 60% of the labels are OTHER / INTERNAL_CONTRADICTION / METHOD_UNSPECIFIED. The v1.5
   matching amendment (page required for generic categories) keeps one generic prediction from matching every such
   label at once; it makes the scores more conservative.

## 3. What the multi-agent design buys (mentor question: "5x cost for a few points - what do you recommend?")

* **Recall.** On the scientific view the full system reaches 78% of the labeled findings (29/37) against 46% for the
  single agent with the same verification. Per protocol: ABC PICU 7/8, SAFER 7/7, INVEST 7/9, fetal cardiac 5/8,
  ALK 3/5. All eight misses are generic `OTHER` labels (data-transfer controls, de-identification timing, consent-role
  wording, missing-value handling, image standardisation): the reviewer either did not raise them or raised them from
  a different page than the labeler quoted (the v1.5 page requirement then counts a miss).
* **Critic.** Across the five protocols the critic verified 112 reviewer findings, sent 14 to a human and rejected or
  withdrew 3; the matched share is 34% among verified vs 21% among unverified. The critic's filtering is in the right
  direction but weak on this set; its clearer contribution is the 36 *critic-raised* issues (always routed to a human,
  never scored) and the revision round that lifted scientific recall from 57% (row 3) to 78% (row 4).
* **Verification layer.** In row 2, 21 of the single agent's 123 findings (17%) could not be located in the PDF or
  cited an invalid guideline code and were demoted to unverified. Those are exactly the findings a committee member
  would otherwise accept as checked. Rows 1 and 2 are two separate model calls, not one output scored twice, so the
  difference between them (precision 29% -> 18%, recall 57% -> 46%) mixes the effect of verification with run-to-run
  variation of the model; a 10-point gap between adjacent rows is within that noise, the 32-point recall gap between
  rows 2 and 4 is not.
* **Recommendation (tiered).** Default: single agent + code verification (row 2) for triage at ~1/6 of the cost;
  full system with the critic for protocols that reach the committee (anything not RETURNED_ADMIN, or on request),
  where recall matters more than cost. The administrative gate stays deterministic in both tiers.

## 4. Mentor question: "which of the four is really an agent?"

The Coordinator is an orchestrator (intake, validation, routing, decision rule, reports); it makes no judgement
calls. The Administrative Review Agent, the Scientific Reviewer and the Scientific Critic are LLM agents with a role,
tools, a bounded authority on the shared state and structured outputs; the critic is the only one that argues with
another agent (one revision round). We say so in the presentation rather than inflating the count.

## 5. Limitations to state plainly

* Five protocols, 46 labels, one annotator, no clinical expert adjudication (Sheba's internal comments were not
  released; the research-authority professor was unavailable). Labels are objective text-level findings only.
* Findings that need clinical judgement are not labeled; when the system reports them they are presented as
  "requires expert verification", never as verified claims.
* Precision against labels is a lower bound (section 2); the 30-finding human check is the complementary measure and
  is pending (Ron, before the mentoring session).
* One run per configuration (no repeats); differences of a few points between rows are not significant.
* The matching rule was amended for generic categories on 29 October before the run (documented, conservative).
* The domain of 16 labels was corrected after the run but before the labeler saw any output (section 2.3); the raw
  table with the labels as first delivered is kept next to the re-scored one.

## 6. Reproducing

```
python eval/protocols/fetch_protocols.py            # PDFs from ClinicalTrials.gov
python eval/ablation.py --cases-glob "nct*.json"    # live run, ~75 min, ~USD 10 (writes reports/results.md)
python eval/rescore.py --stamp <stamp>              # rebuild the tables from the saved findings, no LLM calls
python eval/make_human_check.py --stamp <stamp>     # 30-finding sheet for the human check
```
