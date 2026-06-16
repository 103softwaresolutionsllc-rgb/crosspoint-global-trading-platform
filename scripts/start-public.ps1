# Start dashboard for ngrok public access + verify both are healthy
# Usage: powershell -ExecutionPolicy Bypass -File scripts/start-public.ps1
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$py = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Write-Host "Missing .venv" -ForegroundColor Red
    exit 1
}

$env:PYTHONPATH = Join-Path $Root "src"
$ngrok = "$env:LOCALAPPDATA\Microsoft\WindowsApps\ngrok.exe"
if (-not (Test-Path $ngrok)) { $ngrok = "ngrok" }

function Test-Dashboard {
    try {
        $code = (Invoke-WebRequest -Uri "http://127.0.0.1:8050/login" -UseBasicParsing -TimeoutSec 15).StatusCode
        return $code -eq 200
    } catch { return $false }
}

if (-not (Test-Dashboard)) {
    Write-Host "Starting dashboard on port 8050..." -ForegroundColor Cyan
    Get-NetTCPConnection -LocalPort 8050 -ErrorAction SilentlyContinue |
        ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
    Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -match 'web_dashboard' } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Start-Process -FilePath $py -ArgumentList "web_dashboard.py" -WorkingDirectory $Root -WindowStyle Normal
    Start-Sleep -Seconds 20
}

if (Test-Dashboard) {
    Write-Host "Dashboard OK: http://127.0.0.1:8050/login" -ForegroundColor Green
} else {
    Write-Host "Dashboard failed to start - check the Python window for errors" -ForegroundColor Red
    exit 1
}

$ngrokUp = $false
try {
    $tunnels = (Invoke-RestMethod -Uri "http://127.0.0.1:4040/api/tunnels" -TimeoutSec 3).tunnels
    foreach ($t in $tunnels) {
        if ($t.config.addr -match ":8050$") {
            Write-Host "ngrok OK: $($t.public_url)" -ForegroundColor Green
            Write-Host "Share that URL + login credentials from .env (GTP_DASHBOARD_USER / GTP_DASHBOARD_PASSWORD)" -ForegroundColor Cyan
            $ngrokUp = $true
        }
    }
} catch { }

if (-not $ngrokUp) {
    Write-Host "ngrok not running - starting in a new window..." -ForegroundColor Yellow
    Start-Process -FilePath $ngrok -ArgumentList "http", "8050" -WindowStyle Normal
    Write-Host "After ngrok starts, copy the https://....ngrok-free.app URL from that window" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "Keep BOTH windows open (dashboard + ngrok). Closing either kills the public site." -ForegroundColor Yellow
