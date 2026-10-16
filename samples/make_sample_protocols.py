"""Generate two SYNTHETIC protocol PDFs for development, demos and tests.

* synthetic_protocol_good.pdf   - complete, internally consistent.
* synthetic_protocol_flawed.pdf - documented deficiencies (see eval/labeled_cases/synthetic_flawed.json).

Both are fictional. They cite NCT04470427 (the real registry record of a phase 3
mRNA vaccine trial, enrollment 30,415) only so that the ClinicalTrials.gov
cross-check has something to compare against. Run:  python samples/make_sample_protocols.py
"""
from __future__ import annotations

from pathlib import Path

import pymupdf as fitz

HERE = Path(__file__).parent

COMMON_HEAD = """A Phase 3, Randomized, Observer-Blind, Placebo-Controlled Study to Evaluate the
Efficacy and Safety of Investigational Vaccine VX-101 in Adults
Protocol Number: VX-101-301    ClinicalTrials.gov Identifier: NCT04470427
Protocol Version 2.0    Date: 12 September 2026
Sponsor: Helix Biologics Ltd.
Principal Investigator: Dr. Dana Cohen, Department of Infectious Diseases, Shaare Zedek Medical Center
Contact: dana.cohen@example.org | Tel: +972-2-555-0100
"""

SECTIONS_GOOD = {
    "1. Background and Rationale": """Respiratory infections caused by the target pathogen remain a major cause of morbidity.
VX-101 is an mRNA-based vaccine encoding the stabilised spike glycoprotein. Phase 1/2 studies
(VX-101-101, n = 600) demonstrated an acceptable safety profile and robust neutralising antibody
responses. This Phase 3 trial evaluates efficacy against laboratory-confirmed disease. The placebo
comparator is justified because no licensed vaccine was available at the time of design.""",
    "2. Objectives and Hypotheses": """Primary objective: to demonstrate the efficacy of VX-101 in preventing the first occurrence of
laboratory-confirmed disease starting 14 days after the second dose. Hypothesis: vaccine efficacy > 30%
(lower bound of the 95% confidence interval). Secondary objectives: safety and reactogenicity,
efficacy against severe disease, immunogenicity in a subset.""",
    "3. Trial Design": """Randomized, observer-blind, placebo-controlled, parallel-group superiority trial, allocation ratio 1:1.
Participants receive two intramuscular injections of VX-101 100 micrograms or saline placebo 28 days apart.
The trial is conducted at approximately 100 sites in Israel, Spain and the United States.""",
    "4. Eligibility Criteria": """Inclusion: adults aged 18 years or older; at appreciable risk of exposure; able to provide written informed consent;
agree to use contraception where applicable. Exclusion: known history of the target infection; pregnancy or breastfeeding;
immunosuppressive therapy; receipt of any investigational vaccine within 60 days; known allergy to vaccine components.""",
    "5. Interventions": """VX-101 100 micrograms in 0.5 mL, two doses on Day 1 and Day 29, deltoid muscle. Placebo: 0.9% sodium chloride 0.5 mL.
Intervention is discontinued for anaphylaxis, pregnancy, or participant request. Adherence is recorded in the electronic
case report form. Prohibited concomitant care: other investigational products; permitted: routine medications.""",
    "6. Outcomes": """Primary outcome: first occurrence of symptomatic, laboratory-confirmed disease with onset at least 14 days after the
second dose, analysed as a hazard ratio (vaccine efficacy = 1 - HR) using a stratified Cox model. Secondary outcomes:
severe disease (same definition with hospitalisation), solicited local and systemic adverse reactions within 7 days,
unsolicited adverse events within 28 days, serious adverse events throughout the study, neutralising antibody titres at Day 57.""",
    "7. Participant Timeline": """Screening (Day -28 to 1), Dose 1 (Day 1), Dose 2 (Day 29), follow-up visits Day 57, Month 6, Month 12, Month 24.
Weekly electronic diary for symptom surveillance. Illness visits as needed.""",
    "8. Sample Size": """A total of 30,415 participants will be randomized 1:1. The sample size was calculated to accrue 151 primary endpoint
cases, providing 90% power to demonstrate vaccine efficacy of 60% against a null hypothesis of 30% at a one-sided alpha
of 0.025, assuming an attack rate of 0.75% in the placebo arm over 6 months and 5% dropout (n = 30,415).""",
    "9. Recruitment": """Sites will use community outreach and registries of volunteers. Enrolment of participants over 65 years and
of participants with high-risk comorbidities will be monitored to reach at least 25% of the sample.""",
    "10. Allocation and Blinding": """Randomization uses a centrally generated, computer-generated random sequence with permuted blocks of variable size,
stratified by site and age group, implemented through an interactive web response system (IWRS) ensuring allocation
concealment. Participants, investigators, outcome assessors and sponsor staff are blinded; unblinded pharmacists prepare
the syringes (observer-blind). Emergency unblinding is available 24/7 through the IWRS.""",
    "11. Data Collection, Management and Statistical Analysis": """Data are collected on validated electronic case report forms with range checks and an audit trail. Retention strategies include
reminder calls and travel reimbursement. Statistical analysis plan: the primary analysis uses a stratified Cox proportional
hazards model in the per-protocol efficacy population; sensitivity analysis in the full analysis set; multiple imputation for
missing covariates; pre-specified subgroup analyses by age and comorbidity. Two interim analyses are planned at 53 and 106 cases.""",
    "12. Data Monitoring, Harms and Auditing": """An independent Data Safety Monitoring Board (DSMB) reviews unblinded safety data monthly and conducts the interim efficacy
analyses with O'Brien-Fleming stopping boundaries. Adverse events are graded by FDA toxicity scales; serious adverse events
are reported to the sponsor within 24 hours and to the ethics committee per local regulation. Independent audits occur annually.
Participants may withdraw at any time; stopping rules for the trial include unacceptable safety signals identified by the DSMB.""",
    "13. Ethics, Consent and Confidentiality": """The study will be conducted in accordance with the Declaration of Helsinki, ICH-GCP and the Israeli Public Health
Regulations (Clinical Trials in Human Subjects). Approval of the institutional Helsinki committee (IRB) is required before
enrolment. Written informed consent is obtained by trained study staff before any procedure; the Informed Consent Form is
attached as Appendix A in Hebrew, Arabic, Russian and English. Personal data are pseudonymised; the key is kept at the site.
Insurance: the sponsor holds clinical trial insurance policy HB-2026-301 covering trial-related injury, and participants
are entitled to compensation for trial-related harm. Protocol amendments will be submitted to the committee before implementation.""",
    "14. Dissemination and Data Access": """Results will be published irrespective of outcome within 12 months of database lock; authorship follows ICMJE criteria.
The investigators and an independent statistician have access to the final dataset; de-identified data will be shared on request.
Declaration of interests: investigators receive no personal payments beyond per-participant site fees. Investigator signature
page and CVs are provided in Appendix C. Appendices: A - Informed Consent Form; B - Schedule of Assessments; C - Investigator CVs.""",
}

# Documented deficiencies -> see eval/labeled_cases/synthetic_flawed.json
SECTIONS_FLAWED = dict(SECTIONS_GOOD)
SECTIONS_FLAWED["8. Sample Size"] = """A total of 30,415 participants will be randomized 1:1 (n = 30,415). The study team considers this sufficient."""
SECTIONS_FLAWED["3. Trial Design"] = """Randomized, placebo-controlled, parallel-group Phase 2 superiority trial, allocation ratio 1:1. Approximately 28,000
participants will be enrolled across approximately 100 sites in Israel, Spain and the United States."""
SECTIONS_FLAWED["2. Objectives and Hypotheses"] = SECTIONS_GOOD["2. Objectives and Hypotheses"] + """
The target population is adults aged 18 years or older."""
SECTIONS_FLAWED["4. Eligibility Criteria"] = """Inclusion: adults aged 21 to 65 years; at appreciable risk of exposure; able to provide written informed consent.
Exclusion: known history of the target infection; pregnancy or breastfeeding; immunosuppressive therapy."""
SECTIONS_FLAWED["10. Allocation and Blinding"] = """Participants will be randomized to vaccine or placebo. Participants and investigators are blinded."""
del SECTIONS_FLAWED["13. Ethics, Consent and Confidentiality"]
SECTIONS_FLAWED["13. Ethics and Consent"] = """The study will be conducted in accordance with the Declaration of Helsinki and ICH-GCP. Approval of the institutional
Helsinki committee (IRB) is required before enrolment. Written informed consent is obtained by study staff. Personal
data are pseudonymised."""
del SECTIONS_FLAWED["11. Data Collection, Management and Statistical Analysis"]
SECTIONS_FLAWED["11. Analysis"] = """The primary analysis will compare the two arms. Two interim analyses are planned."""
SECTIONS_FLAWED["14. Dissemination and Data Access"] = """Results will be published. Appendices: B - Schedule of Assessments."""


def build_pdf(path: Path, sections: dict[str, str]):
    doc = fitz.open()
    page = doc.new_page()
    y = 60
    for line in COMMON_HEAD.strip().splitlines():
        page.insert_text((50, y), line.strip(), fontsize=10, fontname="helv")
        y += 14
    y += 20
    for title, body in sections.items():
        text = title + "\n" + " ".join(body.split())
        # wrap manually: ~95 chars per line
        lines = []
        for para in text.split("\n"):
            words, cur = para.split(), ""
            for w in words:
                if len(cur) + len(w) + 1 > 95:
                    lines.append(cur); cur = w
                else:
                    cur = (cur + " " + w).strip()
            lines.append(cur)
        for ln in lines:
            if y > 760:
                page = doc.new_page(); y = 60
            page.insert_text((50, y), ln, fontsize=10 if not ln[:1].isdigit() else 11, fontname="helv")
            y += 13
        y += 12
    doc.save(str(path))
    doc.close()


def main():
    build_pdf(HERE / "synthetic_protocol_good.pdf", SECTIONS_GOOD)
    build_pdf(HERE / "synthetic_protocol_flawed.pdf", SECTIONS_FLAWED)
    print("written:", HERE / "synthetic_protocol_good.pdf", HERE / "synthetic_protocol_flawed.pdf")


if __name__ == "__main__":
    main()
