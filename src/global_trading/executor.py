"""Run one trading workflow tick — shared by CLI and web dashboard."""

from __future__ import annotations

import os
from dataclasses import asdict

from global_trading.agents.execution import ExecutionAgent
from global_trading.agents.market_data import MarketDataAgent
from global_trading.agents.portfolio import PortfolioAgent
from global_trading.agents.risk_agent import RiskAgent
from global_trading.agents.signal import SignalAgent
from global_trading.connectors.fake import FakeConnector
from global_trading.connectors.ibkr import InteractiveBrokersConnector
from global_trading.core.audit import AuditLog
from global_trading.core.domain import Venue
from global_trading.core.ledger import PositionLedger
from global_trading.core.risk import RiskConfig, RiskEngine
from global_trading.core.serde import to_jsonable
from global_trading.observability.logging import configure_logging, get_logger
from global_trading.observability.metrics import Metrics
from global_trading.orchestrator.workflow import TradingWorkflow, WorkflowResult
from global_trading.instruments import (
    analysis_ticker,
    apply_env_defaults,
    apply_spec_to_env,
    parse_instrument_token,
)
from global_trading.settings import load_settings


def _mark_price(ticker: str) -> float:
    try:
        import yfinance as yf

        spec = apply_env_defaults(parse_instrument_token(ticker))
        yf_sym = analysis_ticker(spec)
        hist = yf.Ticker(yf_sym).history(period="5d")["Close"].dropna()
        return float(hist.iloc[-1]) if not hist.empty else 100.0
    except Exception:
        return 100.0


def _serialize_workflow_result(result: WorkflowResult) -> dict:
    return {
        "status": "submitted" if result.order else "skipped",
        "intent": to_jsonable(result.intent) if result.intent else None,
        "risk": asdict(result.risk) if result.risk else None,
        "order": to_jsonable(result.order) if result.order else None,
        "skipped_reason": result.skipped_reason,
    }


def run_workflow_once(
    *,
    ticker: str | None = None,
    use_ibkr: bool = False,
    demo: bool = False,
    asset_class: str | None = None,
) -> dict:
    """
    Run agents → risk → execution once.

    Returns a JSON-serializable dict with status ``submitted`` or ``skipped``.
    """
    s = load_settings()
    audit = AuditLog(s.audit_db_path)
    audit.init()
    configure_logging(json_format=s.log_format == "json")
    metrics = Metrics()
    log = get_logger("gtp.run_once")

    ledger = PositionLedger(account_id="paper-1")
    risk_engine = RiskEngine(
        RiskConfig(
            kill_switch=s.kill_switch,
            max_daily_loss_base=s.max_daily_loss_base,
            base_currency=s.base_currency,
            max_notional_per_order=1_000_000.0,
        )
    )
    raw = (ticker or os.environ.get("GTP_SIGNAL_TICKER", "AAPL")).strip()
    if asset_class and ":" not in raw:
        raw = f"{raw}:{asset_class.lower()}"
    spec = apply_env_defaults(parse_instrument_token(raw))
    apply_spec_to_env(spec)
    sym = spec.raw or spec.symbol
    analysis_sym = analysis_ticker(spec)

    if demo:
        market = MarketDataAgent(marks={"DEMO": 50.0})
        signal = SignalAgent()
    else:
        from fincept_terminal.trading.bridge import ConsensusSignalBridge, ConsensusSignalProvider

        signal = ConsensusSignalProvider(ConsensusSignalBridge(), ticker=raw)
        market = MarketDataAgent(marks={analysis_sym: _mark_price(raw)})

    portfolio = PortfolioAgent()
    risk = RiskAgent(risk_engine)
    execution = ExecutionAgent()

    if not use_ibkr:
        connector: FakeConnector | InteractiveBrokersConnector = FakeConnector(
            account_id="paper-1", metrics=metrics
        )
        venue = Venue.BROKER_GENERIC
        account_id = "paper-1"
        broker_mode = "simulated"
    else:
        connector = InteractiveBrokersConnector(
            account_id="IBKR-PAPER",
            host=s.ibkr_host,
            port=s.ibkr_port,
            client_id=s.ibkr_client_id,
            use_stub=s.ibkr_use_stub,
            metrics=metrics,
        )
        venue = Venue.INTERACTIVE_BROKERS
        account_id = "IBKR-PAPER"
        broker_mode = "stub" if s.ibkr_use_stub else ("paper" if s.ibkr_port == 7497 else "live")

    try:
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
        try:
            result = wf.run_once()
        except RuntimeError as exc:
            payload = {
                "status": "skipped",
                "ticker": sym,
                "broker_mode": broker_mode,
                "intent": None,
                "risk": None,
                "order": None,
                "skipped_reason": str(exc),
            }
            log.info("workflow_skipped", payload=payload)
            return payload

        payload = _serialize_workflow_result(result)
        payload["ticker"] = sym
        payload["broker_mode"] = broker_mode
        log.info("workflow_finished", payload=payload)
        return payload
    finally:
        disconnect = getattr(connector, "disconnect", None)
        if callable(disconnect):
            disconnect()
