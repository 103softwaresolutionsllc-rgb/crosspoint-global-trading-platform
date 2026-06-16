# Crosspoint local dev mode — web dashboard + optional Redis/Celery via Docker
# Usage: pwsh scripts/dev.ps1
#        pwsh scripts/dev.ps1 -Paper          # paper-live IBKR (stub off)
#        pwsh scripts/dev.ps1 -WithDocker     # also start redis + celery worker
param(
    [switch]$Paper,
    [switch]$WithDocker
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Test-Path .env)) {
    if ($Paper) {
        Copy-Item "config\production.example.env" .env
        Write-Host "Created .env from config/production.example.env (paper)" -ForegroundColor Yellow
    } else {
        Copy-Item "config\compliance.example.env" .env
        Write-Host "Created .env from config/compliance.example.env" -ForegroundColor Yellow
    }
}
if (-not (Test-Path var)) { New-Item -ItemType Directory -Path var | Out-Null }

$env:PYTHONPATH = Join-Path $Root "src"
if ($Paper) {
    $env:GTP_IBKR_USE_STUB = "0"
    $env:GTP_IBKR_PORT = "7497"
    $env:GTP_PAPER_FIRST = "true"
} elseif (-not $env:GTP_IBKR_USE_STUB) {
    $env:GTP_IBKR_USE_STUB = "1"
}
if (-not $env:GTP_PAPER_FIRST) { $env:GTP_PAPER_FIRST = "true" }

Write-Host "Installing lightweight dev dependencies..." -ForegroundColor Cyan
python -m pip install -q -e . --no-deps 2>$null
python -m pip install -q structlog rich numpy pandas scipy yfinance requests aiohttp websockets plotly dash pytest pytest-asyncio celery redis

if ($WithDocker) {
    Write-Host "Starting Redis + Celery (docker compose)..." -ForegroundColor Cyan
    docker compose up -d redis
}

Write-Host ""
Write-Host "Crosspoint DEV MODE" -ForegroundColor Green
Write-Host "  Dashboard:  http://127.0.0.1:8050" -ForegroundColor Cyan
Write-Host "  CLI:        fincept macro | fincept consensus --ticker AAPL" -ForegroundColor Cyan
Write-Host "  Workflow:   crosspoint run-once --ticker AAPL" -ForegroundColor Cyan
if ($Paper) {
    Write-Host "  Mode:       PAPER (GTP_IBKR_USE_STUB=0, port 7497)" -ForegroundColor Green
}
Write-Host ""
Write-Host "Starting web dashboard (Ctrl+C to stop)..." -ForegroundColor Yellow
python web_dashboard.py
