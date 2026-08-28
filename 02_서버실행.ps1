$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if (-not (Test-Path ".venv\Scripts\python.exe")) { throw "먼저 01_환경설정.ps1을 실행해주세요." }
& .\.venv\Scripts\python.exe -m uvicorn src.backend.main:app --host 127.0.0.1 --port 8000
