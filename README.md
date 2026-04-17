# Global trading platform

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

## CLI

```bash
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
