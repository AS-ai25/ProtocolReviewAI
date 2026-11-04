"""Build the one-minute demo page (demo/index.html) from a saved full-system run - Hebrew captions, no narration.

    python demo/build_demo.py                      (SAFER, run 20261029-205913)
    python demo/build_demo.py --case nct04084990 --stamp 20261029-205913 --out demo/index.html

The page is a self-contained HTML (images embedded) with seven auto-advancing screens, about 65 seconds in all:
intro, the input protocol, the administrative gate, the scientific reviewer, the critic, the output report, the
Checkpoint 2 numbers. Every finding, quote, page number and verdict shown is read from `outputs/<run>/` - nothing
is typed in by hand. Recording: open the page in a browser, press F11, start the screen recorder, press Space.
Keys: Space = start / pause, arrows = previous / next screen, R = restart.
"""
from __future__ import annotations

import argparse
import base64
import html
import json
import sys
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from protocol_review.config import settings  # noqa: E402

OUTPUTS = settings.output_path

SEV_HE = {"critical": "קריטי", "major": "מהותי", "minor": "קל", "info": "מידע"}
STATUS_HE = {"verified": "מאומת", "unverified": "לא מאומת → לבדיקת אדם", "rejected": "נדחה", "withdrawn": "נמשך"}
DECISION_HE = {"RETURNED_ADMIN": "מוחזר להשלמה אדמיניסטרטיבית", "PASS": "עובר", "NEEDS_HUMAN_REVIEW": "לבדיקת אדם",
               "MAJOR_CONCERNS": "חששות מהותיים"}


def png_b64(doc: pymupdf.Document, page: int, zoom: float = 1.4) -> str:
    pix = doc[page].get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))
    return "data:image/png;base64," + base64.b64encode(pix.tobytes("png")).decode()


def esc(s) -> str:
    return html.escape(str(s if s is not None else ""))


def finding_card(f: dict, *, with_critic: bool = False) -> str:
    ev = (f.get("evidence") or [{}])[0]
    quote = (ev.get("quote") or "").strip()
    if len(quote) > 190:
        quote = quote[:187].rstrip() + "…"
    critic = ""
    if with_critic:
        note = str(f.get("critic_notes") or "")
        if len(note) > 170:
            note = note[:167].rstrip() + "…"
        critic = f'<div class="critic"><span class="tag {f["status"]}">{esc(STATUS_HE.get(f["status"], f["status"]))}</span> <span dir="ltr">{esc(note)}</span></div>'
    page = f'עמ׳ {ev.get("page")}' if ev.get("page") else "לא נמצא במסמך"
    return (f'<div class="card sev-{f["severity"]}"><div class="head"><span class="id" dir="ltr">{esc(f["id"])}</span>'
            f'<span class="sev">{esc(SEV_HE.get(f["severity"], f["severity"]))}</span><span class="ref" dir="ltr">{esc(f.get("guideline_ref") or "")}</span>'
            f'<span class="page">{esc(page)}</span></div><div class="title" dir="ltr">{esc(f["title"])}</div>'
            + (f'<div class="quote" dir="ltr">“{esc(quote)}”</div>' if quote else "") + critic + "</div>")


def build(case: str, stamp: str) -> str:
    run = OUTPUTS / f"abl-agents_full-{case}-{stamp}"
    findings = json.loads((run / "findings.json").read_text(encoding="utf-8"))
    state = json.loads((run / "state.json").read_text(encoding="utf-8"))
    by_id = {f["id"]: f for f in findings}
    meta = state.get("protocol_meta") or {}
    reg = state.get("registry") or {}
    pdf = pymupdf.open(ROOT / "eval" / "protocols" / f"{case}.pdf")
    report = pymupdf.open(run / "final_report.pdf")
    sci_report = pymupdf.open(run / "scientific_report.pdf")
    email_subject = next((ln.split(":", 1)[1].strip() for ln in (run / "email.eml").read_text(encoding="utf-8", errors="replace").splitlines()
                          if ln.lower().startswith("subject:")), "")

    admin = [f for f in findings if f["domain"] == "administrative"]
    admin_block = [f for f in admin if f["severity"] != "info" and f["status"] == "verified"]
    sci = [f for f in findings if f["domain"] == "scientific"]
    n_ver = sum(1 for f in findings if f["status"] == "verified")
    n_unv = sum(1 for f in findings if f["status"] == "unverified")
    n_rej = sum(1 for f in findings if f["status"] in ("rejected", "withdrawn"))
    n_critic_raised = sum(1 for f in findings if f["id"].startswith("SCI-C"))
    n_llm_calls = (state.get("cost") or {}).get("llm_calls", "")

    # pick the examples by severity and a located quote, deterministic order
    def pick(fs, n, want_status=None):
        out = [f for f in fs if (f.get("evidence") or [{}])[0].get("quote") and (want_status is None or f["status"] == want_status)]
        out.sort(key=lambda f: ({"critical": 0, "major": 1, "minor": 2, "info": 3}[f["severity"]], f["id"]))
        return out[:n]

    admin_examples = pick(admin_block, 3) + [f for f in admin_block if not (f.get("evidence") or [{}])[0].get("quote")][:2]
    sci_examples = pick([f for f in sci if f["source"] == "llm"], 3, "verified")
    critic_examples = pick([f for f in sci if f["source"] == "llm" and f["status"] == "verified"], 2) + \
                      [f for f in sci if f["status"] == "unverified" and not f["id"].startswith("SCI-C")][:1]

    decision = state.get("decision", "")
    score = state.get("score")
    if isinstance(score, dict):
        score = score.get("score")
    checklist_unmet = len({f.get("guideline_ref") for f in admin_block if str(f.get("guideline_ref", "")).startswith("ADMIN-CHK")})

    screens = []
    # 1 intro
    screens.append(("10", f"""
<div class="intro">
  <div class="kicker">BIU DS23 · פרויקט גמר · אמיר שמריהו ורון לוי</div>
  <h1>מערכת רב-סוכנית לבדיקת פרוטוקולים של ניסויים קליניים</h1>
  <p class="lead">עוזרת לוועדת הלסינקי: בודקת שלמות ההגשה, סוקרת את המתודולוגיה מול SPIRIT 2025 ומול רישום ClinicalTrials.gov,
  ומחזירה דוח שבו כל ממצא מצביע על עמוד, ציטוט והנחיה. ההחלטה הסופית נשארת בידי אדם.</p>
  <div class="agents">
    <div class="agent"><b>1 · מתאם</b><span>קליטה, אימות JSON, ניתוב, החלטה, דוחות ומייל</span></div>
    <div class="arrow">←</div>
    <div class="agent"><b>2 · בודק אדמיניסטרטיבי</b><span>15 פריטי שלמות הגשה (ADMIN-CHK)</span></div>
    <div class="arrow">←</div>
    <div class="agent"><b>3 · סוקר מדעי</b><span>SPIRIT 2025 · ICH-GCP · רישום הניסוי</span></div>
    <div class="arrow">←</div>
    <div class="agent"><b>4 · מבקר מדעי</b><span>פסק דין לכל ממצא · סבב תיקון אחד</span></div>
  </div>
  <div class="foot">הדגמה על הרצה שמורה מ-29.10.2026 · ללא קריינות</div>
</div>"""))
    # 2 input
    screens.append(("10", f"""
<h2>הקלט: פרוטוקול אמיתי מ-ClinicalTrials.gov</h2>
<div class="two">
  <img class="pageimg" src="{png_b64(pdf, 0)}" alt="">
  <div class="facts">
    <div class="fact"><span>מחקר</span><b dir="ltr">SAFER – Sleep Apnea and Fetal Growth Restriction</b></div>
    <div class="fact"><span>רישום</span><b dir="ltr">{esc(meta.get('nct_id') or case.upper())}</b></div>
    <div class="fact"><span>מסמך</span><b>{esc(meta.get('page_count'))} עמודים · גרסה מתאריך {esc(meta.get('date') or '-')}</b></div>
    <div class="fact"><span>חוקר ראשי</span><b dir="ltr">{esc(meta.get('principal_investigator') or '-')}</b></div>
    <div class="fact"><span>אתרים</span><b>Washington University · הדסה · Rochester</b></div>
    <div class="fact"><span>רישום (API)</span><b dir="ltr">{esc(reg.get('status') or '-')} · phase {esc(reg.get('phase') or '-')} · enrolled {esc(reg.get('enrollment'))}</b></div>
    <p class="note">המתאם מחלץ את הטקסט לפי עמודים, בונה JSON מובנה לפי סעיפים ומריץ 29 בדיקות דטרמיניסטיות לפני שהסוכנים מתחילים.</p>
  </div>
</div>"""))
    # 3 admin gate
    screens.append(("11", f"""
<h2>שלב 1 · השער האדמיניסטרטיבי</h2>
<p class="sub">הבודק האדמיניסטרטיבי עובר על 15 פריטי שלמות. כל ממצא מאומת (למעט "מידע") מחזיר את ההגשה.</p>
<div class="cards">{''.join(finding_card(f) for f in admin_examples[:5])}</div>
<div class="verdict red">{checklist_unmet} מתוך 15 פריטים לא מולאו → <b>{esc(DECISION_HE.get(decision, decision))}</b> · מייל נשלח למזכירות הוועדה
<div class="mail" dir="ltr">✉ {esc(email_subject[:110])}</div></div>"""))
    # 4 scientific reviewer
    screens.append(("12", f"""
<h2>שלב 2 · הסוקר המדעי</h2>
<p class="sub">בהערכה השלב המדעי רץ גם כשהשער נכשל (<span dir="ltr">force_scientific</span>). כל ממצא: עמוד, ציטוט מילולי וקוד SPIRIT 2025.</p>
<div class="cards">{''.join(finding_card(f) for f in sci_examples)}</div>
<div class="verdict">{len(sci)} ממצאים מדעיים · {sum(1 for f in sci if f['source']=='rule')} מהכללים הדטרמיניסטיים · {sum(1 for f in sci if f['source']=='llm' and not f['id'].startswith('SCI-C'))} מהסוקר</div>"""))
    # 5 critic
    screens.append(("11", f"""
<h2>שלב 3 · המבקר המדעי</h2>
<p class="sub">קודם קוד: הציטוט נמצא בעמוד? קוד ההנחיה קיים? אחר כך פסק דין לכל ממצא. מה שלא אומת עובר לאדם, לא נספר כטענה.</p>
<div class="cards">{''.join(finding_card(f, with_critic=True) for f in critic_examples)}</div>
<div class="verdict"><b>{n_ver}</b> מאומתים · <b>{n_unv}</b> לבדיקת אדם · <b>{n_rej}</b> נדחו/נמשכו · <b>{n_critic_raised}</b> נושאים שהמבקר העלה בעצמו</div>"""))
    # 6 output
    screens.append(("10", f"""
<h2>הפלט: דוח לוועדה</h2>
<div class="two">
  <img class="pageimg" src="{png_b64(report, 0)}" alt="">
  <div class="facts">
    <div class="fact"><span>החלטה</span><b>{esc(DECISION_HE.get(decision, decision))}</b></div>
    <div class="fact"><span>ציון</span><b dir="ltr">{esc(score)}/100</b> <small>(ממצאים לא מאומתים לא נספרים)</small></div>
    <div class="fact"><span>דוחות</span><b>סופי · אדמיניסטרטיבי · מדעי (Markdown + PDF)</b></div>
    <div class="fact"><span>לכל ממצא</span><b>סעיף · עמוד · ציטוט · הנחיה · הסבר · פעולה נדרשת</b></div>
    <div class="fact"><span>נשלח</span><b>במייל למזכירות הוועדה עם שלושת ה-PDF</b></div>
    <p class="note">המערכת לא מאשרת פרוטוקול. היא מכינה את העבודה של הוועדה ומסמנת מה דורש בדיקה אנושית.</p>
  </div>
</div>"""))
    # 7 numbers
    screens.append(("9", f"""
<h2>Checkpoint 2 · חמישה פרוטוקולים אמיתיים, תיוג עיוור</h2>
<table class="nums" dir="rtl">
<tr><th></th><th>סוכן יחיד + אימות קוד</th><th>המערכת המלאה (4 סוכנים)</th></tr>
<tr><td>Precision של ממצאים מאומתים (תחום מדעי)</td><td>25%</td><td class="hi">34%</td></tr>
<tr><td>Recall של תוויות אנושיות (תחום מדעי)</td><td>46%</td><td class="hi">78%</td></tr>
<tr><td>טוקנים לפרוטוקול</td><td>~40k</td><td>~250k</td></tr>
</table>
<p class="lead small">המלצה מדורגת: סוכן יחיד + אימות לסינון ראשוני; המערכת המלאה לפרוטוקולים שמגיעים לדיון בוועדה.
בדיקה אנושית של 30 ממצאים מאומתים: הציטוט תומך בממצא ב-1, חלקית ב-5, לא ב-24. אימות אוטומטי אינו הוכחה; האדם מכריע.</p>
<div class="foot" dir="ltr">github.com/Ron-levi1/Clinical-Trial-Protocol-Review-System · run abl-agents_full-{esc(case)}-{esc(stamp)}</div>"""))

    body = "".join(f'<section data-sec="{secs}">{content}</section>' for secs, content in screens)
    return TEMPLATE.replace("{{BODY}}", body).replace("{{N}}", str(len(screens)))


TEMPLATE = r"""<!doctype html>
<html lang="he" dir="rtl"><head><meta charset="utf-8"><title>ProtocolReviewAI – demo</title>
<style>
:root{--bg:#0e1420;--fg:#eef2f7;--mut:#9fb0c6;--acc:#5cc8ff;--red:#ff6b6b;--amb:#ffc857;--grn:#7bd389;--card:#162033;--line:#26324a}
*{box-sizing:border-box}html,body{height:100%;margin:0;background:var(--bg);color:var(--fg);font-family:"Segoe UI","Noto Sans Hebrew",Arial,sans-serif}
section{display:none;position:absolute;inset:0;padding:38px 64px 56px;flex-direction:column}section.on{display:flex}
h1{font-size:44px;line-height:1.2;margin:10px 0 18px}h2{font-size:34px;margin:0 0 6px;color:var(--acc)}
.kicker{color:var(--mut);font-size:18px;letter-spacing:.3px}.lead{font-size:21px;line-height:1.55;max-width:1150px;color:#d7e0ec}.lead.small{font-size:18px}
.sub{color:var(--mut);font-size:18px;margin:0 0 14px}
.agents{display:flex;align-items:stretch;gap:10px;margin:26px 0 10px}.agent{flex:1;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px;display:flex;flex-direction:column;gap:6px}
.agent b{font-size:19px}.agent span{color:var(--mut);font-size:15px}.arrow{align-self:center;color:var(--acc);font-size:30px}
.foot{margin-top:auto;color:var(--mut);font-size:14px}
.two{display:flex;gap:34px;flex:1;min-height:0}.pageimg{height:min(74vh,720px);border-radius:8px;box-shadow:0 8px 30px #0008;background:#fff}
.facts{display:flex;flex-direction:column;gap:12px;font-size:19px;max-width:720px}.fact span{display:inline-block;min-width:130px;color:var(--mut)}.fact b{font-weight:600}
.note{color:#c6d2e2;font-size:17px;line-height:1.5;margin-top:10px}
.cards{display:flex;flex-direction:column;gap:9px;flex:1;min-height:0;overflow:hidden}
.card{background:var(--card);border:1px solid var(--line);border-right:6px solid var(--mut);border-radius:10px;padding:9px 14px}
.card.sev-critical{border-right-color:var(--red)}.card.sev-major{border-right-color:var(--amb)}.card.sev-minor{border-right-color:var(--acc)}
.head{display:flex;gap:14px;align-items:center;color:var(--mut);font-size:14px}.head .id{font-family:Consolas,monospace;color:var(--fg)}
.head .sev{font-weight:700}.sev-critical .sev{color:var(--red)}.sev-major .sev{color:var(--amb)}.sev-minor .sev{color:var(--acc)}
.title{font-size:18px;margin:3px 0;text-align:left}.quote{font-size:15px;color:#c6d2e2;font-style:italic;text-align:left}
.critic{margin-top:5px;font-size:14px;color:#c6d2e2}.tag{display:inline-block;padding:1px 8px;border-radius:999px;font-size:13px;font-weight:700;background:#2a3b57}
.tag.verified{background:#1f4d2e;color:var(--grn)}.tag.unverified{background:#4d3a1f;color:var(--amb)}
.verdict{margin-top:12px;background:#132a1c;border:1px solid #1f4d2e;border-radius:10px;padding:12px 16px;font-size:19px}
.verdict.red{background:#2d1619;border-color:#5a2a2f}.mail{margin-top:6px;font-size:14px;color:var(--mut);text-align:left}
.nums{border-collapse:collapse;font-size:21px;margin:18px 0}.nums th,.nums td{border:1px solid var(--line);padding:10px 18px;text-align:center}.nums td:first-child{text-align:right}
.nums .hi{color:var(--grn);font-weight:700;font-size:24px}
#bar{position:fixed;left:0;bottom:0;height:6px;background:var(--acc);width:0}
#hint{position:fixed;left:16px;bottom:14px;color:var(--mut);font-size:13px;direction:ltr}#ctr{position:fixed;right:16px;bottom:14px;color:var(--mut);font-size:13px}
</style></head><body>
{{BODY}}
<div id="bar"></div><div id="hint">Space start/pause · ← → · R restart</div><div id="ctr"></div>
<script>
const secs=[...document.querySelectorAll('section')];let i=0,t0=0,run=false,raf;
function show(n){i=Math.max(0,Math.min(secs.length-1,n));secs.forEach((s,k)=>s.classList.toggle('on',k===i));t0=performance.now();
  document.getElementById('ctr').textContent=(i+1)+' / '+secs.length;}
function tick(){if(!run)return;const d=+secs[i].dataset.sec*1000,e=performance.now()-t0;
  document.getElementById('bar').style.width=Math.min(100,100*e/d)+'%';
  if(e>=d){if(i<secs.length-1)show(i+1);else{run=false;document.getElementById('bar').style.width='100%';return}}raf=requestAnimationFrame(tick)}
document.addEventListener('keydown',ev=>{if(ev.code==='Space'){ev.preventDefault();run=!run;if(run){t0=performance.now()-(t0?0:0);tick()}}
  else if(ev.key==='ArrowRight'){show(i+1)}else if(ev.key==='ArrowLeft'){show(i-1)}else if(ev.key==='r'||ev.key==='R'){run=false;show(0)}});
show(0);
</script></body></html>"""


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):      # Windows consoles default to cp1252
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--case", default="nct04084990")
    ap.add_argument("--stamp", default="20261029-205913")
    ap.add_argument("--out", default=str(ROOT / "demo" / "index.html"))
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build(a.case, a.stamp), encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
