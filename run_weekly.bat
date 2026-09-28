@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m funnel.run %*
) else (
    py -3 -m funnel.run %*
)
exit /b %errorlevel%
