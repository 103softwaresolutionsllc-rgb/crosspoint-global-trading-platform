from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from global_trading.agents.execution import ExecutionAgent
from global_trading.agents.market_data import MarketDataAgent
from global_trading.agents.portfolio import PortfolioAgent
from global_trading.agents.risk_agent import RiskAgent
from global_trading.agents.signal import SignalAgent, StaticIntentSignal
from global_trading.connectors.fake import FakeConnector
from global_trading.connectors.ibkr import InteractiveBrokersConnector
from global_trading.connectors.reconcile import reconcile_positions
from global_trading.core.audit import AuditLog
from global_trading.core.domain import (
    AssetClass,
    InstrumentId,
    OrderSide,
    OrderType,
    TradeIntent,
    Venue,
)
from global_trading.core.ledger import PositionLedger
from global_trading.core.risk import RiskConfig, RiskEngine
from global_trading.core.serde import to_jsonable
from global_trading.observability.logging import configure_logging, get_logger
from global_trading.observability.metrics import Metrics
from global_trading.executor import run_workflow_once
from global_trading.orchestrator.workflow import WorkflowResult
from global_trading.settings import load_settings


_CROSSPOINT_CYAN = "#25E7FF"
_CROSSPOINT_DARK = "#0B1020"


def _print_banner(console: Console, prog: str) -> None:
    title = Text("CROSSPOINT", style=f"bold {_CROSSPOINT_CYAN}")
    subtitle = Text("multi-agent trading platform", style="bold #A9B4C4")
    body = Text()
    body.append_text(title)
    body.append("\n")
    body.append_text(subtitle)
    body.append("\n\n")
    body.append("Command: ", style="bold #A9B4C4")
    body.append(prog, style=f"bold {_CROSSPOINT_CYAN}")

    console.print(
        Panel(
            body,
            border_style=_CROSSPOINT_CYAN,
            style=f"on {_CROSSPOINT_DARK}",
            padding=(1, 2),
        )
    )


def _build_common() -> tuple[AuditLog, Metrics]:
    s = load_settings()
    audit = AuditLog(s.audit_db_path)
    audit.init()
    configure_logging(json_format=s.log_format == "json")
    return audit, Metrics()


def _serialize_workflow_result(result: WorkflowResult) -> dict:
    return {
        "intent": to_jsonable(result.intent) if result.intent else None,
        "risk": asdict(result.risk) if result.risk else None,
        "order": to_jsonable(result.order) if result.order else None,
        "skipped_reason": result.skipped_reason,
    }


def _mark_price(ticker: str) -> float:
    try:
        import yfinance as yf

        hist = yf.Ticker(ticker).history(period="5d")["Close"].dropna()
        return float(hist.iloc[-1]) if not hist.empty else 100.0
    except Exception:
        return 100.0


def cmd_run_once(args: argparse.Namespace) -> int:
    ticker = (args.ticker or os.environ.get("GTP_SIGNAL_TICKER", "AAPL")).upper()
    payload = run_workflow_once(
        ticker=ticker,
        use_ibkr=args.ibkr,
        demo=args.demo,
        asset_class=getattr(args, "asset_class", None),
    )
    if payload.get("order"):
        print(json.dumps(payload["order"], indent=2))
    else:
        print(json.dumps({"skipped": payload.get("skipped_reason")}, indent=2))
    return 0


def cmd_reconcile(args: argparse.Namespace) -> int:
    s = load_settings()
    _, metrics = _build_common()
    log = get_logger("gtp.reconcile")
    ledger = PositionLedger(account_id="paper-1")
    if not args.ibkr:
        fc = FakeConnector(account_id="paper-1", metrics=metrics)
        remote = fc.get_positions()
        local = ledger.positions()
        rep = reconcile_positions(
            account_id="paper-1", venue=Venue.BROKER_GENERIC, local=local, remote=remote
        )
    else:
        ib = InteractiveBrokersConnector(
            account_id="IBKR-PAPER",
            host=s.ibkr_host,
            port=s.ibkr_port,
            client_id=s.ibkr_client_id,
            use_stub=s.ibkr_use_stub,
            metrics=metrics,
        )
        try:
            remote = ib.get_positions()
            local: list = []
            rep = reconcile_positions(
                account_id="IBKR-PAPER", venue=Venue.INTERACTIVE_BROKERS, local=local, remote=remote
            )
        finally:
            ib.disconnect()
    log.info("reconciliation", ok=rep.ok, mismatches=len(rep.mismatches))
    print(json.dumps(to_jsonable(rep), indent=2))
    return 0 if rep.ok else 1


def cmd_metrics(_args: argparse.Namespace) -> int:
    _, metrics = _build_common()
    print(json.dumps(metrics.snapshot(), indent=2))
    return 0


def cmd_crypto_once(args: argparse.Namespace) -> int:
    s = load_settings()
    audit, metrics = _build_common()
    log = get_logger("gtp.crypto_once")
    if args.stub or not s.crypto_api_key:
        log.warning("crypto_stub_or_missing_keys", stub=args.stub, has_key=bool(s.crypto_api_key))
        connector = FakeConnector(account_id="crypto-paper", metrics=metrics)
        venue = Venue.CRYPTO_CEX
        account_id = "crypto-paper"
    else:
        try:
            from global_trading.connectors.crypto_ccxt import CCXTCryptoConnector
        except ImportError as e:
            log.error("ccxt_not_installed", hint='pip install "global-trading-platform[crypto]"')
            raise SystemExit(1) from e
        connector = CCXTCryptoConnector(
            exchange_id=s.crypto_exchange,
            api_key=s.crypto_api_key,
            api_secret=s.crypto_api_secret,
            sandbox=s.crypto_sandbox,
            account_id="crypto-live",
            metrics=metrics,
        )
        venue = Venue.CRYPTO_CEX
        account_id = "crypto-live"

    ledger = PositionLedger(account_id=account_id)
    risk_engine = RiskEngine(
        RiskConfig(
            kill_switch=s.kill_switch,
            max_daily_loss_base=s.max_daily_loss_base,
            base_currency=s.base_currency,
            max_notional_per_order=5_000.0,
        )
    )
    market = MarketDataAgent(marks={"BTC/USDT": 60_000.0})
    intent = TradeIntent(
        instrument=InstrumentId(
            symbol="BTC/USDT",
            venue=venue,
            asset_class=AssetClass.CRYPTO,
            quote_currency="USDT",
        ),
        side=OrderSide.BUY,
        quantity=float(args.qty),
        order_type=OrderType.MARKET,
        rationale="cli crypto demo",
        strategy_name="crypto_demo",
    )
    signal = StaticIntentSignal(intent, strategy_name="crypto_demo")
    portfolio = PortfolioAgent()
    risk = RiskAgent(risk_engine)
    execution = ExecutionAgent()

    wf = TradingWorkflow(
        market_data=market,
        signal=signal,
        portfolio=portfolio,
        risk=risk,
        execution=execution,
        connector=connector,
        venue=venue,
        account_id=account_id,
        audit=audit,
        ledger=ledger,
        metrics=metrics,
    )
    result = wf.run_once()
    log.info("crypto_workflow", payload=_serialize_workflow_result(result))
    if result.order:
        print(json.dumps(to_jsonable(result.order), indent=2))
    else:
        print(json.dumps({"skipped": result.skipped_reason}, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="crosspoint",
        description="Crosspoint CLI (multi-agent trading platform). 'gtp' is supported as an alias.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run-once", help="Run one workflow tick through risk and execution")
    r.add_argument(
        "--ibkr",
        action="store_true",
        help="Use Interactive Brokers adapter (set GTP_IBKR_USE_STUB=0 for live TWS)",
    )
    r.add_argument("--ticker", default=None, help="Signal ticker (default: GTP_SIGNAL_TICKER or AAPL)")
    r.add_argument(
        "--asset-class",
        default=None,
        choices=["equity", "future", "option", "fx"],
        help="Asset class (default: GTP_ASSET_CLASS or equity)",
    )
    r.add_argument("--demo", action="store_true", help="Use legacy DEMO signal instead of live consensus")
    r.set_defaults(func=cmd_run_once)

    rec = sub.add_parser("reconcile", help="Reconcile local vs remote positions")
    rec.add_argument("--ibkr", action="store_true", help="Use IBKR adapter for remote positions")
    rec.set_defaults(func=cmd_reconcile)

    m = sub.add_parser("metrics", help="Print in-process metrics snapshot")
    m.set_defaults(func=cmd_metrics)

    c = sub.add_parser("crypto-once", help="Run one crypto intent (uses fake connector without API keys)")
    c.add_argument("--stub", action="store_true", help="Force fake connector")
    c.add_argument("--qty", default="0.001", help="Order quantity (small default)")
    c.set_defaults(func=cmd_crypto_once)

    return p


def main(argv: list[str] | None = None) -> None:
    load_settings()
    argv = argv if argv is not None else sys.argv[1:]
    parser = build_parser()
    args = parser.parse_args(argv)

    # A small, logo-matching terminal UI flourish. Opt-out via env or flag if needed later.
    console = Console()
    invoked_as = (sys.argv[0] or "").split("\\")[-1].split("/")[-1]
    prog = invoked_as or "crosspoint"
    try:
        _print_banner(console, prog=prog)
    except Exception:
        # Never block trading actions on UI concerns.
        pass
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
