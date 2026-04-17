# Local smoke: install dev deps, tests, CLI, then optional IBKR/CCXT extras when supported.
# Run from repo root: pwsh scripts/verify.ps1
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Invoke-Step([string]$Label, [scriptblock]$Block) {
    Write-Host "==> $Label" -ForegroundColor Cyan
    & $Block
    if ($LASTEXITCODE -ne 0) { throw "Step failed: $Label (exit $LASTEXITCODE)" }
}

Invoke-Step "pip install -e .[dev]" { python -m pip install -e ".[dev]" }
Invoke-Step "pytest" { python -m pytest }
Invoke-Step "cli run-once" { python -m global_trading.cli run-once }
Invoke-Step "cli reconcile" { python -m global_trading.cli reconcile }
Invoke-Step "cli crypto-once" { python -m global_trading.cli crypto-once }

$py = python -c "import sys; print(sys.version_info.major, sys.version_info.minor)" 2>$null
$parts = $py -split " "
$major = [int]$parts[0]
$minor = [int]$parts[1]
if ($major -eq 3 -and $minor -ge 15) {
    Write-Warning "Skipping .[ibkr] and .[crypto] on Python 3.15+ (manylinux wheels often missing). Use Python 3.11-3.13 for full extras."
    exit 0
}

Invoke-Step "pip install -e .[ibkr]" { python -m pip install -e ".[ibkr]" }
Invoke-Step "pip install -e .[crypto]" { python -m pip install -e ".[crypto]" }
Write-Host "All verification steps completed." -ForegroundColor Green
