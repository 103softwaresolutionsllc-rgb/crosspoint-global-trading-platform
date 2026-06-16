# Agent auto-pilot - runs consensus workflow on a schedule
# Reads GTP_WATCHLIST and GTP_AUTOPILOT_* from .env (CLI flags override .env).
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts/autopilot.ps1
#   powershell -ExecutionPolicy Bypass -File scripts/autopilot.ps1 -Ibkr
#   powershell -ExecutionPolicy Bypass -File scripts/autopilot.ps1 -Simulate -Tickers "AAPL,NVDA"
param(
    [int]$IntervalMinutes = 0,
    [string]$Tickers = "",
    [switch]$Ibkr,
    [switch]$Simulate
)

$ErrorActionPreference = "Stop"
# Python writes warnings to stderr; don't treat those as fatal PowerShell errors.
$PSNativeCommandUseErrorActionPreference = $false
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Test-Path .env)) {
    Write-Host "Missing .env - copy config\production.example.env to .env first." -ForegroundColor Red
    exit 1
}

$env:PYTHONPATH = Join-Path $Root "src"
$py = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }

if (-not (Test-Path var)) { New-Item -ItemType Directory -Path var | Out-Null }
$log = Join-Path $Root "var\autopilot.log"

function Write-Log($msg) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $msg"
    Add-Content -Path $log -Value $line
    Write-Host $line
}

function Get-EnvValue($key, $default = "") {
    if (Test-Path ".env") {
        foreach ($line in Get-Content ".env" -Encoding UTF8) {
            $line = $line.Trim()
            if ($line -and -not $line.StartsWith("#") -and $line -match "^$([regex]::Escape($key))=(.+)$") {
                return $matches[1].Trim().Trim('"').Trim("'")
            }
        }
    }
    return $default
}

if ($IntervalMinutes -le 0) {
    $envInterval = Get-EnvValue "GTP_AUTOPILOT_INTERVAL_MINUTES" "30"
    if ($envInterval -match "^\d+$") {
        $IntervalMinutes = [int]$envInterval
    } else {
        $IntervalMinutes = 30
    }
}

if (-not $Ibkr -and -not $Simulate) {
    $ibkrEnv = Get-EnvValue "GTP_AUTOPILOT_IBKR" ""
    if ($ibkrEnv -eq "1" -or $ibkrEnv -ieq "true") {
        $Ibkr = $true
    }
}

$ibkrFlag = ""
if ($Ibkr) { $ibkrFlag = "--ibkr" }
if ($Simulate) { $ibkrFlag = "" }

function Get-WatchlistFromEnv {
    $raw = Get-EnvValue "GTP_WATCHLIST" "AAPL"
    return $raw
}

if ($Tickers) {
    $list = $Tickers.Split(",") | ForEach-Object { $_.Trim().ToUpper() } | Where-Object { $_ }
} else {
    $watchlistRaw = Get-WatchlistFromEnv
    $list = $watchlistRaw.Split(",") | ForEach-Object { $_.Trim().ToUpper() } | Where-Object { $_ }
}

Write-Log "AUTO-PILOT START interval=$IntervalMinutes min tickers=$($list -join ',') ibkr=$([bool]$Ibkr) simulate=$([bool]$Simulate)"
Write-Log "Logs: $log"
Write-Log "Stop with Ctrl+C. Set GTP_KILL_SWITCH=true in .env to block orders."

while ($true) {
    foreach ($t in $list) {
        Write-Log "RUN $t"
        $cliArgs = @("-m", "global_trading.cli", "run-once", "--ticker", $t)
        if ($ibkrFlag) { $cliArgs += $ibkrFlag }
        $prev = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        try {
            & $py @cliArgs 2>&1 | ForEach-Object { Write-Log $_ }
        } finally {
            $ErrorActionPreference = $prev
        }
    }
    Write-Log "SLEEP $IntervalMinutes min"
    Start-Sleep -Seconds ($IntervalMinutes * 60)
}
