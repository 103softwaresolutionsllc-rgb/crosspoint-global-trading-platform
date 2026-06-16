# Verify .env is present and loaded by Crosspoint
# Usage: powershell -ExecutionPolicy Bypass -File scripts/verify-env.ps1
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Test-Path .env)) {
    Write-Host "MISSING: .env not found at $Root\.env" -ForegroundColor Red
    Write-Host "Run: copy config\production.example.env .env" -ForegroundColor Yellow
    exit 1
}

$env:PYTHONPATH = Join-Path $Root "src"
$py = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }

Write-Host "Loading .env from repo root..." -ForegroundColor Cyan
& $py -c @"
from global_trading.settings import load_settings, _repo_root
s = load_settings()
print('  .env file:   ', _repo_root() / '.env')
print('  IBKR stub:   ', s.ibkr_use_stub, '(0=real paper/live, 1=simulated)')
print('  IBKR port:   ', s.ibkr_port, '(7497=paper, 7496=live)')
print('  Signal:      ', __import__('os').environ.get('GTP_SIGNAL_TICKER', 'AAPL'))
auth = __import__('os').environ.get('GTP_DASHBOARD_AUTH_ENABLED', '0')
user = __import__('os').environ.get('GTP_DASHBOARD_USER', '')
print('  Dashboard auth:', 'on (' + user + ')' if auth.strip().lower() in ('1','true','yes','on') else 'off')
print('  Watchlist:   ', __import__('os').environ.get('GTP_WATCHLIST', ''))
print('  Autopilot:   ', __import__('os').environ.get('GTP_AUTOPILOT_INTERVAL_MINUTES', '30'), 'min, IBKR=', __import__('os').environ.get('GTP_AUTOPILOT_IBKR', '0'))
print('  Portfolio:   ', __import__('os').environ.get('GTP_PORTFOLIO_VALUE', ''))
print('  Order qty:   ', __import__('os').environ.get('GTP_BASE_ORDER_QTY', ''))
fred = __import__('os').environ.get('FRED_API_KEY', '')
print('  FRED key:    ', 'set' if fred else 'MISSING')
"@
