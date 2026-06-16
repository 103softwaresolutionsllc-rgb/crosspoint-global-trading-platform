# Verify Crosspoint setup and launch the web dashboard
# Usage: powershell -ExecutionPolicy Bypass -File scripts/finish-setup.ps1
param([switch]$SkipDashboard)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Test-Path .env)) {
    Write-Host "Missing .env — run: powershell -File scripts/setup-paper.ps1" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path .venv\Scripts\python.exe)) {
    Write-Host "Creating virtual environment..." -ForegroundColor Cyan
    python -m venv .venv
    .venv\Scripts\python.exe -m pip install -q --upgrade pip
    .venv\Scripts\python.exe -m pip install -q -e . --no-deps
    .venv\Scripts\python.exe -m pip install -q structlog rich numpy pandas scipy yfinance requests aiohttp websockets plotly dash PyQt6 scikit-learn sqlalchemy redis celery ib-insync fredapi openai anthropic alembic fastapi uvicorn
}
if (-not (Test-Path var)) { New-Item -ItemType Directory -Path var | Out-Null }

$env:PYTHONPATH = Join-Path $Root "src"
$py = Join-Path $Root ".venv\Scripts\python.exe"

Write-Host "`n=== Crosspoint setup check ===" -ForegroundColor Green

Write-Host "[1/3] Loading live dashboard state..." -ForegroundColor Cyan
& $py -c "from fincept_terminal.dashboard.phase2_state import load_dashboard_state; s=load_dashboard_state(); print('  OK  signal=', s.signal_ticker, ' broker=', s.broker_mode, ' agents=', len(s.agents))"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[2/3] Testing IBKR connection (port 7497 paper)..." -ForegroundColor Cyan
& $py -m global_trading.cli reconcile --ibkr
if ($LASTEXITCODE -ne 0) {
    Write-Host "  IBKR not reachable — start TWS/IB Gateway on port 7497, enable API, then re-run." -ForegroundColor Yellow
} else {
    Write-Host "  IBKR connected." -ForegroundColor Green
}

if ($SkipDashboard) { exit 0 }

Write-Host "[3/3] Starting web dashboard at http://127.0.0.1:8050 ..." -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop.`n" -ForegroundColor Yellow
& $py web_dashboard.py
