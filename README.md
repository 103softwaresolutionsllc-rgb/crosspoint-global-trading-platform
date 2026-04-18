# Crosspoint

Multi-agent trading core with pluggable connectors (paper/live broker, crypto CEX). See `RUNBOOK.md` for operations and `config/compliance.example.env` for compliance-related settings.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
# Optional Interactive Brokers: pip install -e ".[ibkr]"
# Optional CEX (CCXT): pip install -e ".[crypto]"
```

Copy `config/compliance.example.env` to `.env` and set variables. Use paper trading first.

Optional extras `[ibkr]` and `[crypto]` need pre-built wheels for native dependencies; use **Python 3.11–3.13** if installs fail on newer interpreters.

## One-shot verification

Runs tests, CLI smoke commands, then optional IBKR/CCXT installs (skipped automatically on Python 3.15+ where wheels are often missing).

- Windows: `pwsh scripts/verify.ps1`, or Windows PowerShell: `powershell -ExecutionPolicy Bypass -File scripts/verify.ps1`
- macOS/Linux: `bash scripts/verify.sh`

## CLI

```bash
# New primary command (recommended)
crosspoint run-once
crosspoint reconcile
crosspoint crypto-once
crosspoint metrics

# Backwards-compatible alias
gtp run-once
gtp reconcile
gtp crypto-once
gtp metrics
# Optional: IB adapter (respect GTP_IBKR_USE_STUB for simulation)
gtp run-once --ibkr
```

## Tests

```bash
pytest
```
