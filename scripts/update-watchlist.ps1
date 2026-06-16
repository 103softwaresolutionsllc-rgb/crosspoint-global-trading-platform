# Refresh GTP_WATCHLIST from Yahoo Finance screeners (no API key required)

# Usage:

#   powershell -ExecutionPolicy Bypass -File scripts/update-watchlist.ps1

#   powershell -ExecutionPolicy Bypass -File scripts/update-watchlist.ps1 -Screener day_gainers

#   powershell -ExecutionPolicy Bypass -File scripts/update-watchlist.ps1 -Count 20 -Merge

#   powershell -ExecutionPolicy Bypass -File scripts/update-watchlist.ps1 -DryRun

param(

    [ValidateSet("most_actives", "day_gainers", "day_losers")]

    [string]$Screener = "most_actives",

    [int]$Count = 15,

    [switch]$Merge,

    [switch]$DryRun

)



$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot

Set-Location $Root



if (-not (Test-Path .env)) {

    Write-Host "Missing .env - copy config\production.example.env to .env first." -ForegroundColor Red

    exit 1

}



$py = Join-Path $Root ".venv\Scripts\python.exe"

if (-not (Test-Path $py)) { $py = "python" }



function Get-EnvValue($key) {

    foreach ($line in Get-Content ".env" -Encoding UTF8) {

        $line = $line.Trim()

        if ($line -and -not $line.StartsWith("#") -and $line -match "^$([regex]::Escape($key))=(.+)$") {

            return $matches[1].Trim().Trim('"').Trim("'")

        }

    }

    return ""

}



Write-Host "Fetching $Count tickers from Yahoo screener: $Screener ..." -ForegroundColor Cyan

$fetchScript = @"

import json, sys, urllib.request

screener, count = sys.argv[1], int(sys.argv[2])

url = (

    'https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved'

    f'?formatted=true&lang=en-US&region=US&scrIds={screener}&count={count}'

)

req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})

data = json.load(urllib.request.urlopen(req, timeout=20))

quotes = data['finance']['result'][0]['quotes']

syms = [q['symbol'] for q in quotes if q.get('symbol')]

print(','.join(syms))

"@



$newRaw = & $py -c $fetchScript $Screener $Count

if (-not $newRaw) {

    Write-Host "No tickers returned from Yahoo." -ForegroundColor Red

    exit 1

}



$newList = $newRaw.Split(",") | ForEach-Object { $_.Trim().ToUpper() } | Where-Object { $_ }



if ($Merge) {

    $existingRaw = Get-EnvValue "GTP_WATCHLIST"

    $existing = @()

    if ($existingRaw) {

        $existing = $existingRaw.Split(",") | ForEach-Object { $_.Trim().ToUpper() } | Where-Object { $_ }

    }

    $seen = @{}

    $merged = @()

    foreach ($t in ($existing + $newList)) {

        if (-not $seen.ContainsKey($t)) {

            $seen[$t] = $true

            $merged += $t

        }

    }

    $newList = $merged

}



$watchlist = $newList -join ","

Write-Host "Watchlist ($($newList.Count) tickers): $watchlist" -ForegroundColor Green



if ($DryRun) {

    Write-Host "Dry run - .env not modified." -ForegroundColor Yellow

    exit 0

}



$updated = $false

$lines = Get-Content ".env" -Encoding UTF8 | ForEach-Object {

    if ($_ -match "^GTP_WATCHLIST=") {

        $updated = $true

        "GTP_WATCHLIST=$watchlist"

    } else {

        $_

    }

}

if (-not $updated) {

    $lines += "GTP_WATCHLIST=$watchlist"

}

$lines | Set-Content ".env" -Encoding UTF8

Write-Host "Updated .env GTP_WATCHLIST. Restart dashboard/autopilot to pick up changes." -ForegroundColor Cyan

