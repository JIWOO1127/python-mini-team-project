$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    $launcher = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } elseif (Get-Command python -ErrorAction SilentlyContinue) { "python" } else { throw "Python 3.10 이상을 설치한 뒤 다시 실행해주세요." }
    & $launcher -m venv .venv
}

& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host ".env 파일을 만들었습니다. API 키를 입력해주세요." -ForegroundColor Yellow
}

Write-Host "환경 설정이 완료되었습니다." -ForegroundColor Green
