# Paper-trading environment setup for Crosspoint
# Usage: pwsh scripts/setup-paper.ps1
#        pwsh scripts/setup-paper.ps1 -FredKey "your_fred_api_key"
param(
    [string]$FredKey = "",
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$template = "config\production.example.env"
$target = ".env"

if (-not (Test-Path $template)) {
    Write-Error "Missing template: $template"
}

if ((Test-Path $target) -and -not $Force) {
    Write-Host ".env already exists. Re-run with -Force to overwrite, or edit .env manually." -ForegroundColor Yellow
    exit 0
}

Copy-Item $template $target -Force

$content = Get-Content $target -Raw
$content = $content -replace 'GTP_IBKR_USE_STUB=0', 'GTP_IBKR_USE_STUB=0'
$content = $content -replace 'GTP_IBKR_PORT=7497', 'GTP_IBKR_PORT=7497'
$content = $content -replace 'GTP_PAPER_FIRST=true', 'GTP_PAPER_FIRST=true'
$content = $content -replace 'GTP_KILL_SWITCH=false', 'GTP_KILL_SWITCH=false'

if ($FredKey) {
    $content = $content -replace 'FRED_API_KEY=', "FRED_API_KEY=$FredKey"
}

Set-Content -Path $target -Value $content -NoNewline

if (-not (Test-Path var)) { New-Item -ItemType Directory -Path var | Out-Null }

Write-Host ""
Write-Host "Paper trading .env created at $target" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Add FRED_API_KEY to .env (https://fred.stlouisfed.org/docs/api/api_key.html)"
Write-Host "  2. Start IBKR TWS or Gateway on port 7497 (paper account)"
Write-Host "  3. Web dashboard:  pwsh scripts/dev.ps1 -Paper"
Write-Host "  4. Qt desktop:     `$env:PYTHONPATH='src'; python -m fincept_terminal"
Write-Host "  5. One workflow:     crosspoint run-once --ticker AAPL"
Write-Host ""
