@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
  set "PYTHON_CMD=python"
) else (
  set "PYTHON_CMD=py"
)

if not exist ".venv\Scripts\python.exe" (
  %PYTHON_CMD% -m venv .venv
  if errorlevel 1 goto :error
)

.venv\Scripts\python.exe -m pip install --upgrade pip
if errorlevel 1 goto :error
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto :error

if not exist ".env" copy ".env.example" ".env" >nul
echo.
echo Environment setup is complete.
echo Check .env and enter the Kakao and KMA API keys if needed.
pause
exit /b 0

:error
echo.
echo Setup failed. Check that Python is installed and try again.
pause
exit /b 1
