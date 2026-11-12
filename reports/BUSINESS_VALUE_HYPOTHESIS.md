# Business Value Hypothesis | Clinical Protocol Review System

**Project:** DS23 Multi-Agent Clinical Trial Protocol Review System  
**Date:** 12 November 2026  
**Status:** Preliminary business-value hypothesis. Not a measured efficiency or ROI result.

## The operational problem

Administrative staff and scientific reviewers spend substantial time assessing
clinical research protocol submissions, locating relevant details, identifying
missing information, preparing clarifications, and reviewing revised documents.

The proposed product is an **AI-assisted preliminary review tool**. It can
organize potential findings and supporting references for human review. It does
not approve studies or replace the Helsinki committee, scientific reviewers,
clinical investigators, or other authorized decision-makers.

## Value proposition

1. **Administrative review:** Less repetitive searching and more structured
   identification of missing information, potentially reducing preparation and
   follow-up work for the committee secretariat.
2. **Scientific review:** An organized first-pass report can help physicians
   and scientific reviewers focus their expertise on substantive questions
   rather than on locating every relevant passage manually.
3. **Institutional capacity:** If measured review time is reduced without
   compromising safety or quality, staff may have more capacity to review
   additional submissions and clinicians may redirect time to patient care
   or other research activities.
4. **Long-term opportunity:** More effective research operations may improve
   researcher experience and support additional studies. Extra approvals,
   sponsored-research income and clinical capacity are **possible downstream
   benefits**, not automatic or currently established outcomes.

## The 2-3 hour working estimate

The project team estimates that **approximately 2-3 combined staff-hours
per protocol** may be involved in administrative and preliminary scientific
review. This is an **unverified assumption about manual effort**, not a
measured time saving caused by the software.

The system cannot claim to save all 2-3 hours, because staff must still
check the AI findings, resolve incorrect claims, and make the actual decision.

| Monthly protocols (illustrative) | Manual hours associated with review at 2 h each | At 3 h each |
|---:|---:|---:|
| 20 | 40 | 60 |
| 40 | 80 | 120 |
| 60 | 120 | 180 |

**These are workload scenarios, not demonstrated saved hours and not Sheba
activity statistics.** Do not present them as a measured outcome.

## How to measure actual savings

```
Net staff-hours saved / protocol
  = baseline administrative + preliminary scientific staff-hours
    - assisted administrative + scientific staff-hours
    - verification, corrections, follow-up and escalation hours

Monthly net hours released
  = monthly review volume x measured net hours saved / protocol
```

Measure the baseline and assisted workflow on comparable cases. Track
time spent on unsupported findings, staff rework, administrative returns,
turnaround time, serious misses, model usage, infrastructure and maintenance.
Report the median and range, ideally by study type and by reviewer role.

Financial return requires a separate model with validated labor-cost
assumptions, AI operating cost and any genuinely incremental research revenue.
Freed staff-hours are capacity, not automatically payroll savings or revenue.

## Safety and scientific limitations

Prior human evidence review found that many technically `verified` findings
were not adequately supported by their quoted evidence. A poor-quality
first-pass review can **increase**, rather than decrease, staff work.

Failures of the LLM or tools must never result in an automatic PASS.
Where a review is incomplete or uncertain, human review is required.
The product is decision support, not an autonomous regulatory approval tool.

## Proposed 10-slide presentation message

**Potential business impact:** Preliminary administrative and scientific
review may require around 2-3 combined staff-hours per protocol (team
estimate; pending validation). A structured, human-supervised AI review
may reduce repetitive screening and free capacity for more studies and
clinical work. The actual net time saving, quality, costs and any
incremental hospital revenue will be established in a controlled pilot.

## Evidence needed to substantiate the business case

- Administrative staff time per protocol and per clarification cycle.
- Scientific reviewer time per protocol.
- Monthly protocol volume, segmented by study type.
- Assisted-review time, including checking false positives and omissions.
- Infrastructure and model operating cost per case.
- Whether increased processing capacity leads to more studies actually
  initiated, and whether they add positive financial contribution.
