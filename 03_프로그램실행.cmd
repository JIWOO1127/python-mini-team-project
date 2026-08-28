@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo 먼저 01_환경설정.cmd를 실행해주세요.
  pause
  exit /b 1
)
.venv\Scripts\python.exe run_app.py
