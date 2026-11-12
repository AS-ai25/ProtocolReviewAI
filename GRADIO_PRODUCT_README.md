# Clinical Protocol Review | End-user Gradio app

A separate user-facing app for the existing FastAPI review engine. This add-on does not change the agents, pipeline, scores, rules, or research evaluation data.

## Run locally (Windows)

Open two terminals in the main repository folder after installing the existing project dependencies.

```powershell
.venv\Scripts\python -m pip install -r requirements-gradio.txt
```

Terminal 1: start the existing backend

```powershell
.venv\Scripts\python -m uvicorn protocol_review.api:app --port 8040
```

Terminal 2: start the product

```powershell
.venv\Scripts\python gradio_app.py
```

Open http://127.0.0.1:7860

Gradio 6 is required (`css` and `theme` are `launch()` arguments from Gradio 6 on). The backend's `WEBHOOK_SECRET` from `.env` must be given to the product as `PROTOCOL_WEBHOOK_SECRET`.

If your backend uses a custom `WEBHOOK_SECRET`, set `PROTOCOL_WEBHOOK_SECRET` in terminal 2 before launching. The default matches the project's current `change-me` development setting and **must be replaced for deployment**.

## Live progress

After **Start full protocol review** the page follows the run by itself: a *Live progress* box shows the current stage (intake, administrative screening, scientific review, critic, decision) and the latest pipeline steps, refreshed every few seconds with read-only calls. When the review finishes, the results open automatically in the *Review Results* tab. On Windows, `start_demo.bat` starts the service and this product together and opens both pages.

## Safe demo

Opening the product, refreshing history, loading a saved run, and downloading its report do not trigger LLM calls. Only clicking **Start full protocol review** triggers a new paid review. You must tick a confirmation checkbox first. This interface deliberately excludes force-scientific evaluation bypass, experimental model configurations and developer statistics.

## Email

Email preview does not send mail. No email is sent on upload, review completion, report export, or preview. The only manual send action is the **Send email** button after confirmation, and sending is disabled by default. To enable it on a controlled local/organizational machine, configure environment variables:

```text
PROTOCOL_UI_ALLOW_EMAIL=true
PROTOCOL_UI_SMTP_HOST=your-approved-smtp-server
PROTOCOL_UI_SMTP_PORT=587
PROTOCOL_UI_SMTP_FROM=approved-sender@organization.org
PROTOCOL_UI_SMTP_USER=optional-username
PROTOCOL_UI_SMTP_PASSWORD=optional-password
```

The application requires an explicit checkbox and a click for every send. It attaches the saved final Markdown report. Only enable this with an approved mail service and authorization for the recipient and content. It cannot bypass organizational restrictions.

## Important limitations

- Research prototype, not an approved clinical decision system.
- Gradio UI is bound to localhost, with no public share link.
- FastAPI backend exposes read endpoints without authentication in the current repository. Do **not** expose backend or Gradio to the public internet. Add enterprise SSO/access controls and per-user authorization before production.
- The existing backend has its own automatic notification pathway (`notify_boss`). For a safe demonstration, leave `EMAIL_DRY_RUN=true` (the project default) even when testing this new UI. The Gradio product now blocks starting a review when `/health` reports `email_dry_run` is not `true`, so the backend notification pathway cannot send mail for runs started through this UI. This guard does not control reviews initiated outside the Gradio app. Keep `EMAIL_DRY_RUN=true` on the server.
- Report files are saved to private temporary folders for download. Define retention/deletion policies for real use.
- Historical runs require the original SQLite database. A new clone may show no history.
- A technical `verified` status does not prove claim correctness. Human assessment remains necessary.
- Do not submit confidential patient/hospital data without the appropriate institutional approval and data processing arrangements.

## Language policy (English-only edition)

All Gradio interface labels, executive summaries, finding descriptions, evidence excerpts, report exports and email content use the source English wording returned by the backend. No translation model, translation API key, or extra translation calls are used. This frontend does not change the backend model prompts or the scientific review logic.

## Share with the project maintainer

Copy these three files to the root of the existing repository. Keep the backend and evaluation files as they are. For email, set approved SMTP parameters and explicitly enable sending only in the authorized demo environment. Sending always requires a user action and confirmation.
