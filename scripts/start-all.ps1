# Start dashboard + optional autopilot
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts/start-all.ps1
#   powershell -ExecutionPolicy Bypass -File scripts/start-all.ps1 -Autopilot
param([switch]$Autopilot)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Test-Path .venv\Scripts\python.exe)) {
    Write-Host "Missing .venv - run: python -m venv .venv" -ForegroundColor Red
    exit 1
}

$env:PYTHONPATH = Join-Path $Root "src"
$py = Join-Path $Root ".venv\Scripts\python.exe"

# Free port 8050 if an old dashboard is stuck
$pids = Get-NetTCPConnection -LocalPort 8050 -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty OwningProcess -Unique
foreach ($pid in $pids) {
    Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
}

Write-Host "Starting dashboard at http://127.0.0.1:8050 ..." -ForegroundColor Cyan
Start-Process -FilePath $py -ArgumentList "web_dashboard.py" -WorkingDirectory $Root -WindowStyle Normal

Start-Sleep -Seconds 12
try {
    $code = (Invoke-WebRequest -Uri "http://127.0.0.1:8050/login" -UseBasicParsing -TimeoutSec 30).StatusCode
    Write-Host "Dashboard is UP (HTTP $code) — keep the Python window open" -ForegroundColor Green
} catch {
    Write-Host "Dashboard may still be loading - open http://127.0.0.1:8050/login" -ForegroundColor Yellow
}
Write-Host "For ngrok: run 'ngrok http 8050' in another window (needs dashboard + ngrok both running)" -ForegroundColor DarkGray

if ($Autopilot) {
    Write-Host "Starting autopilot in this window (Ctrl+C to stop)..." -ForegroundColor Cyan
    & "$Root\scripts\autopilot.ps1"
}
