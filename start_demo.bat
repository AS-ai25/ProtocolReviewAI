@echo off
rem One-click start for a demo or a recording (Windows): the FastAPI service (port 8040) and the end-user
rem Gradio product (port 7860), each in its own window, then both pages in the default browser.
rem The webhook secret is read from .env and handed to the product; nothing is written anywhere.
rem Close the two windows to stop.
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo .venv not found. Create it and install requirements.txt and requirements-gradio.txt first.
  pause
  exit /b 1
)
set "PROTOCOL_WEBHOOK_SECRET=change-me"
if exist ".env" for /f "usebackq tokens=1,* delims==" %%A in (".env") do if /i "%%A"=="WEBHOOK_SECRET" set "PROTOCOL_WEBHOOK_SECRET=%%B"
set "PYTHONIOENCODING=utf-8"

start "Protocol Review API (port 8040)" cmd /k ".venv\Scripts\python.exe -m protocol_review.cli serve --port 8040"
echo Waiting for the API ...
timeout /t 8 /nobreak >nul
start "Protocol Review product (port 7860)" cmd /k ".venv\Scripts\python.exe gradio_app.py"
echo Waiting for the product ...
timeout /t 12 /nobreak >nul

rem The dashboard upload form asks for the webhook secret: put it on the clipboard so it can be pasted (Ctrl+V).
echo|set /p="%PROTOCOL_WEBHOOK_SECRET%"|clip
start "" "http://127.0.0.1:7860/"
start "" "http://localhost:8040/dashboard#review"
echo.
echo Product (end user):   http://127.0.0.1:7860/
echo Dashboard (research): http://localhost:8040/dashboard
echo Two windows are running the servers. Close them to stop.
echo The webhook secret is on the clipboard: paste it (Ctrl+V) into the "webhook secret" field of the dashboard.
timeout /t 5 >nul
