@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -m aldines gui
) else (
  python -m aldines gui
)
if errorlevel 1 pause
