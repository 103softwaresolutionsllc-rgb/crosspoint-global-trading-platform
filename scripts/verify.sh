#!/usr/bin/env bash
# Local smoke: install dev deps, tests, CLI, then optional IBKR/CCXT extras when supported.
# Run from repo root: bash scripts/verify.sh
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

step() {
  echo "==> $1"
  shift
  "$@"
}

step "pip install -e .[dev]" python -m pip install -e ".[dev]"
step "pytest" python -m pytest
step "cli run-once" python -m global_trading.cli run-once
step "cli reconcile" python -m global_trading.cli reconcile
step "cli crypto-once" python -m global_trading.cli crypto-once

minor="$(python -c 'import sys; print(sys.version_info.minor)')"
major="$(python -c 'import sys; print(sys.version_info.major)')"
if [[ "$major" -eq 3 && "$minor" -ge 15 ]]; then
  echo "Skipping .[ibkr] and .[crypto] on Python 3.15+ (pre-built wheels often missing). Use Python 3.11-3.13 for full extras." >&2
  exit 0
fi

step "pip install -e .[ibkr]" python -m pip install -e ".[ibkr]"
step "pip install -e .[crypto]" python -m pip install -e ".[crypto]"
echo "All verification steps completed."
