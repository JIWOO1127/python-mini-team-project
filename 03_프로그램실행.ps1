$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if (-not (Test-Path ".venv\Scripts\python.exe")) { throw "먼저 01_환경설정.ps1을 실행해주세요." }
try { Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -TimeoutSec 3 | Out-Null }
catch { throw "서버가 실행 중이 아닙니다. 별도 PowerShell에서 02_서버실행.ps1을 먼저 실행해주세요." }
& .\.venv\Scripts\python.exe -m src.ui
