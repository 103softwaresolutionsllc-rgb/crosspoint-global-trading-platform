# Operations runbook

## Kill switch

Set `GTP_KILL_SWITCH=true` in the environment (or `.env`) and restart any running workers. The risk engine blocks new orders while the flag is set. Remove the flag only after confirming strategy and connectivity.

## Daily loss limit

`GTP_MAX_DAILY_LOSS_BASE` caps realized PnL in base currency for the risk layer. Tune with paper trading; the engine must be fed PnL via `RiskEngine.record_pnl` in production pipelines (wire from fills).

## Paper before live

Keep `GTP_PAPER_FIRST=true` and use broker paper or `GTP_IBKR_USE_STUB=1` until reconciliation passes consistently. For crypto, use testnet/sandbox keys (`GTP_CRYPTO_SANDBOX=1`) before production API keys.

## Reconciliation failures

1. Run `crosspoint reconcile` (or `--ibkr` when using that adapter). (`gtp` is a supported alias.)
2. If `ok` is false, compare `local_qty` vs `remote_qty` in the report.
3. Pull broker/exchange blotter and match `client_order_id` in the audit DB (`audit_events` table in `var/audit.sqlite3`).
4. Halt trading if unexplained drift persists after two consecutive checks.

## Incident checklist

1. Enable kill switch.
2. Capture last 200 audit rows (SQLite query or app helper).
3. Export metrics snapshot (`crosspoint metrics` / `gtp metrics`).
4. Disconnect optional IB sessions (`InteractiveBrokersConnector.disconnect` in long-running processes).

## Logs

Structured logs go to stdout in JSON when `GTP_LOG_FORMAT=json`. Ship to your log stack from the process manager.
