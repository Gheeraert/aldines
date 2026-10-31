@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -m aldines gui aldines.json
) else (
  python -m aldines gui aldines.json
)
if errorlevel 1 pause
