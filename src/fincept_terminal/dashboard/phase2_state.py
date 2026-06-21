"""
Dashboard state — live agent consensus, broker positions, and execution bridge.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import numpy as np
import yfinance as yf

import asyncio

from fincept_terminal.agents.base import Recommendation
from fincept_terminal.agents.macro_context import MacroSnapshot, get_macro_context
from fincept_terminal.agents.orchestration.consensus import AgentConsensus
from fincept_terminal.agents.orchestration.ipo_screener import IpoSuggestion, fetch_ipo_suggestions_sync
from fincept_terminal.agents.orchestration.screener import AgentScreener
from fincept_terminal.trading.bridge import BridgeConfig, ConsensusSignalBridge
from global_trading.agents.portfolio import PortfolioAgent, SizingConfig
from global_trading.backtest.engine import BacktestConfig, BacktestEngine
from global_trading.connectors.ibkr import InteractiveBrokersConnector
from global_trading.core.domain import AssetClass, OrderSide
from global_trading.instruments import analysis_ticker, apply_env_defaults, parse_instrument_token
from global_trading.execution.slippage import SlippageConfig, estimate_slippage
from global_trading.execution.sor import BrokerScore, SmartOrderRouter
from global_trading.settings import load_settings


@dataclass
class AgentStripItem:
    name: str
    score: float
    delta: float
    color: str


@dataclass
class PositionItem:
    ticker: str
    side: str
    quantity: str
    pnl: float
    pnl_pct: float
    sparkline: list[float] = field(default_factory=list)


@dataclass
class WorkflowItem:
    name: str
    meta: str
    icon: str
    icon_class: str
    badge: str
    badge_class: str


@dataclass
class TickerTapeItem:
    symbol: str
    label: str
    price: float
    change_pct: float


@dataclass
class NewsItem:
    symbol: str
    title: str
    publisher: str
    link: str
    published: str


TAPE_SYMBOLS = ["SPY", "QQQ", "AAPL", "NVDA", "MSFT", "GOOGL", "META", "BTC-USD", "^VIX"]
NEWS_SYMBOLS = ["SPY", "AAPL", "NVDA", "QQQ"]

AGENT_META: dict[str, dict[str, str]] = {
    "Warren Buffett": {"short": "Buffett", "color": "#00ff88", "strategy": "Value · Moat depth"},
    "Benjamin Graham": {"short": "Graham", "color": "#ffb347", "strategy": "Deep value · Net-net"},
    "Peter Lynch": {"short": "Lynch", "color": "#00d4ff", "strategy": "GARP · PEG ratio"},
    "Ian Dunlap": {"short": "Dunlap", "color": "#9b8cff", "strategy": "Turnaround · Cost cuts"},
    "Jim Simons": {"short": "Simons", "color": "#00ffcc", "strategy": "Quant · Stat arb"},
    "Ray Dalio": {"short": "Dalio", "color": "#ff6b6b", "strategy": "Macro · Risk parity"},
}


@dataclass
class Phase2DashboardState:
    macro: MacroSnapshot
    market_pills: list[dict[str, str]]
    consensus: list[AgentStripItem]
    execution: dict[str, Any]
    agents: list[dict[str, Any]]
    workflows: list[WorkflowItem]
    risk: dict[str, Any]
    positions: list[PositionItem]
    backtest: dict[str, Any]
    ticker_tape: list[TickerTapeItem] = field(default_factory=list)
    news_items: list[NewsItem] = field(default_factory=list)
    ipo_suggestions: list[IpoSuggestion] = field(default_factory=list)
    timestamp: str = ""
    signal_ticker: str = ""
    watchlist: list[str] = field(default_factory=list)
    broker_mode: str = "disconnected"
    broker_connected: bool = False
    account_cash: float | None = None
    account_equity: float | None = None
    portfolio_value: float = 100_000.0
    broker_error: str | None = None
    data_source: str = ""


def _empty_execution(*, ticker: str = "—", gate_reason: str = "loading") -> dict[str, Any]:
    settings = load_settings()
    var_cap = settings.max_daily_loss_base * 0.8
    return {
        "ticker": ticker,
        "algo": "—",
        "raw_qty": 0,
        "sized_qty": 0,
        "broker": "—",
        "broker_score": 0.0,
        "slippage_bps": 0.0,
        "avg_slippage_bps": 0.0,
        "var_cap": var_cap,
        "post_trade_var": 0.0,
        "var_ok": False,
        "route_steps": ["Signal", "VaR gate", "Size", "SOR", "VWAP", "Fill"],
        "active_steps": 1,
        "gate_open": False,
        "gate_reason": gate_reason,
        "rationale": gate_reason,
    }


def placeholder_dashboard_state() -> Phase2DashboardState:
    """Fast shell for first paint — avoids 60s+ blocking before ngrok/browser time out."""
    watchlist = _env_watchlist()
    signal_ticker = _env_signal_ticker(watchlist)
    dd_limit = float(os.environ.get("GTP_MAX_DRAWDOWN_PCT", "10"))
    macro = MacroSnapshot(
        gdp_growth_yoy=0.0,
        cpi_yoy=0.0,
        unemployment=0.0,
        fed_funds_rate=0.0,
        yield_curve_10y2y=0.0,
        regime="loading",
        as_of="",
        source="loading",
    )
    execution = _empty_execution(ticker=signal_ticker, gate_reason="Connecting to agents and broker…")
    return Phase2DashboardState(
        macro=macro,
        market_pills=[{"label": "Loading live data…", "class": "pill-warn"}],
        consensus=[],
        execution=execution,
        agents=[],
        workflows=[],
        risk={
            "var_95": 0.0,
            "sharpe": 0.0,
            "max_dd": 0.0,
            "dd_limit": dd_limit,
            "dd_pct_of_limit": 0,
            "sizing_model": "VaR-scaled",
        },
        positions=[],
        backtest={
            "ticker": signal_ticker,
            "sharpe": 0.0,
            "max_dd": 0.0,
            "win_rate": 0.0,
            "total_return": 0.0,
        },
        timestamp=datetime.now().strftime("%H:%M ET"),
        signal_ticker=signal_ticker,
        watchlist=watchlist,
        broker_mode="loading",
        data_source="loading · please wait 30–60s",
    )


def _env_watchlist() -> list[str]:
    raw = os.environ.get("GTP_WATCHLIST", "AAPL,MSFT,GOOGL,AMZN,NVDA,META,TSLA,NFLX")
    out: list[str] = []
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        if ":" in token:
            parts = token.split(":")
            parts[0] = parts[0].upper()
            out.append(":".join(parts))
        else:
            out.append(token.upper())
    return out


def _env_signal_ticker(watchlist: list[str]) -> str:
    return os.environ.get("GTP_SIGNAL_TICKER", watchlist[0] if watchlist else "AAPL").upper()


def _dashboard_ibkr_client_id(settings) -> int:
    """Use a separate client ID from autopilot/CLI to avoid Gateway disconnects."""
    raw = os.environ.get("GTP_IBKR_DASHBOARD_CLIENT_ID", "").strip()
    if raw.isdigit():
        return int(raw)
    return settings.ibkr_client_id + 1


def _env_portfolio_value() -> float:
    return float(os.environ.get("GTP_PORTFOLIO_VALUE", "100000"))


def _yf_symbol(ticker: str) -> str:
    try:
        spec = apply_env_defaults(parse_instrument_token(ticker))
        return analysis_ticker(spec)
    except Exception:
        return ticker.replace("/", "-")


def _tape_label(symbol: str) -> str:
    return symbol.replace("-USD", "").replace("^", "")


def _run_async(coro):
    try:
        return asyncio.run(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()


def _parse_news_raw(raw: dict, symbol: str) -> NewsItem | None:
    content = raw.get("content") or raw
    title = content.get("title") or raw.get("title", "")
    if not title:
        return None
    provider = content.get("provider") or {}
    publisher = provider.get("displayName") or raw.get("publisher", "") or "Yahoo Finance"
    link = raw.get("link", "")
    for key in ("clickThroughUrl", "canonicalUrl"):
        url_obj = content.get(key) or raw.get(key)
        if isinstance(url_obj, dict) and url_obj.get("url"):
            link = url_obj["url"]
            break
    pub_raw = content.get("displayTime") or content.get("pubDate") or raw.get("providerPublishTime") or ""
    published = ""
    if pub_raw:
        try:
            if isinstance(pub_raw, (int, float)):
                published = datetime.fromtimestamp(pub_raw).strftime("%H:%M")
            else:
                published = datetime.fromisoformat(str(pub_raw).replace("Z", "+00:00")).strftime("%H:%M")
        except Exception:
            published = str(pub_raw)[:16]
    return NewsItem(symbol=_tape_label(symbol), title=title, publisher=publisher, link=link, published=published)


def fetch_ticker_tape(symbols: list[str] | None = None) -> list[TickerTapeItem]:
    symbols = symbols or TAPE_SYMBOLS
    items: list[TickerTapeItem] = []
    for sym in symbols:
        yf_sym = _yf_symbol(sym)
        try:
            hist = yf.Ticker(yf_sym).history(period="5d")
            closes = hist["Close"].dropna()
            if closes.empty:
                continue
            price = float(closes.iloc[-1])
            change_pct = 0.0
            if len(closes) >= 2:
                change_pct = (price / float(closes.iloc[-2]) - 1) * 100
            items.append(TickerTapeItem(yf_sym, _tape_label(sym), price, change_pct))
        except Exception:
            continue
    return items


def fetch_market_news(symbols: list[str] | None = None, per_symbol: int = 3, max_items: int = 12) -> list[NewsItem]:
    symbols = symbols or NEWS_SYMBOLS
    seen: set[str] = set()
    items: list[NewsItem] = []
    for sym in symbols:
        yf_sym = _yf_symbol(sym)
        try:
            for raw in (yf.Ticker(yf_sym).news or [])[:per_symbol]:
                parsed = _parse_news_raw(raw, sym)
                if not parsed or parsed.title in seen:
                    continue
                seen.add(parsed.title)
                items.append(parsed)
        except Exception:
            continue
    return items[:max_items]


def _fetch_sparkline(ticker: str, days: int = 30) -> list[float]:
    try:
        sym = "BTC-USD" if ticker.startswith("BTC") else _yf_symbol(ticker)
        hist = yf.Ticker(sym).history(period=f"{days}d")
        if hist.empty:
            return []
        return [float(c) for c in hist["Close"].dropna().tolist()[-30:]]
    except Exception:
        return []


def _load_macro() -> MacroSnapshot:
    return _run_async(get_macro_context())


def _broker_mode_label(settings, *, connected: bool) -> str:
    if settings.ibkr_use_stub:
        return "stub"
    if not connected:
        return "disconnected"
    if settings.ibkr_port == 7496:
        return "live"
    return "paper"


def _balance_amount(balances: dict, tag: str, currency: str) -> float | None:
    key = f"{tag}:{currency}"
    if key in balances:
        return float(balances[key].amount)
    for money in balances.values():
        if money.currency == currency:
            return float(money.amount)
    return None


def _load_broker_snapshot(settings) -> tuple[list[PositionItem], bool, float | None, float | None, str | None]:
    """Load IBKR positions and account balances; disconnect when done."""
    connector = InteractiveBrokersConnector(
        account_id="IBKR-PAPER",
        host=settings.ibkr_host,
        port=settings.ibkr_port,
        client_id=_dashboard_ibkr_client_id(settings),
        use_stub=settings.ibkr_use_stub,
    )
    currency = settings.base_currency or "USD"
    try:
        try:
            raw = connector.get_positions()
            balances = connector.get_balances()
            cash = _balance_amount(balances, "TotalCashValue", currency)
            equity = _balance_amount(balances, "NetLiquidation", currency)
            if equity is None and cash is not None:
                equity = cash
            connected = True
            error = None
        except Exception as exc:
            return [], False, None, None, str(exc)

        items: list[PositionItem] = []
        for pos in raw:
            if abs(pos.quantity) < 1e-9:
                continue
            inst = pos.instrument
            if inst.asset_class == AssetClass.FUTURES:
                token = f"{inst.symbol}:future"
            elif inst.asset_class == AssetClass.FX:
                token = f"{inst.symbol}:fx"
            elif inst.asset_class == AssetClass.CRYPTO:
                token = f"{inst.symbol}:crypto"
            elif inst.asset_class == AssetClass.OPTION:
                expiry = inst.extra.get("expiry")
                strike = inst.extra.get("strike")
                right = inst.extra.get("right") or "C"
                if expiry and strike:
                    token = f"{inst.symbol}:option:{expiry}:{strike}:{right}"
                else:
                    token = f"{inst.symbol}:option"
            else:
                token = inst.symbol

            # Resolve to valid yfinance symbol
            yf_sym = _yf_symbol(token)
            try:
                mark = float(yf.Ticker(yf_sym).history(period="5d")["Close"].dropna().iloc[-1])
            except Exception:
                mark = float(pos.avg_price or 0)
            avg = float(pos.avg_price or mark)
            pnl = (mark - avg) * pos.quantity
            pnl_pct = ((mark / avg) - 1) * 100 if avg else 0.0
            side = "Long" if pos.quantity > 0 else "Short"
            qty_label = f"{abs(pos.quantity):g} shares"
            if inst.symbol.startswith("BTC"):
                qty_label = f"{abs(pos.quantity):g} BTC"
            items.append(
                PositionItem(token, side, qty_label, round(pnl, 2), round(pnl_pct, 2), _fetch_sparkline(token))
            )
        return items, connected, cash, equity, error
    finally:
        connector.disconnect()


def _consensus_strip_from_results(agent_results, prev_scores: dict[str, float] | None = None) -> list[AgentStripItem]:
    prev_scores = prev_scores or {}
    strip: list[AgentStripItem] = []
    for ar in agent_results:
        meta = AGENT_META.get(ar.agent_name, {"short": ar.agent_name, "color": "#00d4ff"})
        short = meta["short"]
        delta = ar.confidence - prev_scores.get(short, ar.confidence)
        strip.append(AgentStripItem(short, round(ar.confidence, 2), round(delta, 2), meta["color"]))
    return strip


def _signal_class(rec: Recommendation) -> tuple[str, str]:
    if rec in (Recommendation.STRONG_BUY, Recommendation.BUY):
        return "BUY", "buy"
    if rec in (Recommendation.STRONG_SELL, Recommendation.SELL):
        return "SELL", "sell"
    return "HOLD", "hold"


def _agent_cards_from_consensus(
    consensus,
    watchlist: list[str],
    macro_pill: str,
    passed_tickers: set[str],
    watchlist_len: int,
) -> list[dict]:
    cards: list[dict] = []
    for ar in consensus.agent_results:
        meta = AGENT_META.get(ar.agent_name, {"short": ar.agent_name, "color": "#00d4ff", "strategy": ""})
        signal, signal_class = _signal_class(ar.recommendation)
        tickers = [(t, t in passed_tickers) for t in watchlist[:6]]
        cards.append(
            {
                "name": meta["short"],
                "strategy": meta["strategy"],
                "signal": signal,
                "signal_class": signal_class,
                "score": round(ar.confidence, 2),
                "screened": watchlist_len,
                "color": meta["color"],
                "macro_pill": macro_pill,
                "tickers": tickers,
            }
        )
    return cards


async def _load_live_analysis(signal_ticker: str, watchlist: list[str], macro: MacroSnapshot):
    signal_spec = apply_env_defaults(parse_instrument_token(signal_ticker))
    signal_analysis = analysis_ticker(signal_spec)
    screen_syms = [analysis_ticker(apply_env_defaults(parse_instrument_token(t))) for t in watchlist]
    consensus = await AgentConsensus(enable_debate=True).analyze(signal_analysis, macro=macro)
    screen = await AgentScreener(min_consensus_score=0.5).screen(screen_syms)
    bridge = ConsensusSignalBridge(
        config=BridgeConfig(
            min_consensus_score=0.5,
            base_quantity=float(os.environ.get("GTP_BASE_ORDER_QTY", "100")),
            portfolio_value=_env_portfolio_value(),
            require_liquidity_clear=False,
        )
    )
    bridge_result = await bridge.evaluate(signal_ticker, macro=macro)
    return consensus, screen, bridge_result


def _compute_execution_pipeline(bridge_result, settings, portfolio_value: float) -> dict[str, Any]:
    var_cap = settings.max_daily_loss_base * 0.8
    consensus = bridge_result.consensus
    ticker = consensus.ticker if consensus else os.environ.get("GTP_SIGNAL_TICKER", "AAPL")

    if bridge_result.intent is None:
        reason = bridge_result.skipped_reason or "no trade signal"
        return _empty_execution(ticker=ticker, gate_reason=reason)

    intent = bridge_result.intent
    ticker = intent.instrument.symbol
    raw_qty = float(intent.quantity)
    try:
        yf_sym = analysis_ticker(apply_env_defaults(parse_instrument_token(ticker)))
        mark_price = float(yf.Ticker(yf_sym).history(period="5d")["Close"].dropna().iloc[-1])
    except Exception:
        mark_price = 100.0

    var_per_share = mark_price * 0.02
    target_var_fraction = min(0.08, (raw_qty * var_per_share) / portfolio_value)
    sized = PortfolioAgent(
        SizingConfig(
            portfolio_value=portfolio_value,
            var_fraction=target_var_fraction,
            var_per_share=var_per_share,
            max_position_pct=0.15,
        )
    ).adjust_intent(intent, mark_price=mark_price)

    class _BrokerAdapter:
        def __init__(self, broker_id: str) -> None:
            self.broker_id = broker_id

    router = SmartOrderRouter()
    router.register(_BrokerAdapter("ibkr"), BrokerScore("ibkr", latency_ms=12, fill_rate=0.99, fee_bps=0.5))
    router.register(_BrokerAdapter("alpaca"), BrokerScore("alpaca", latency_ms=45, fill_rate=0.94, fee_bps=0.0))
    broker = router.select_broker() or "ibkr"
    broker_score = router._scores[broker].composite_score
    slip_bps = (estimate_slippage(mark_price, quantity=sized.quantity, config=SlippageConfig(bps=5)) / mark_price) * 10_000
    post_trade_var = -(sized.quantity * var_per_share)
    var_ok = abs(post_trade_var) < var_cap

    return {
        "ticker": ticker,
        "algo": "VWAP",
        "raw_qty": int(raw_qty),
        "sized_qty": int(sized.quantity),
        "broker": broker.upper(),
        "broker_score": round(broker_score, 2),
        "slippage_bps": round(slip_bps, 1),
        "avg_slippage_bps": round(slip_bps * 0.85, 1),
        "var_cap": var_cap,
        "post_trade_var": post_trade_var,
        "var_ok": var_ok,
        "route_steps": ["Signal", "VaR gate", "Size", "SOR", "VWAP", "Fill"],
        "active_steps": 6 if var_ok else 3,
        "gate_open": var_ok,
        "gate_reason": "" if var_ok else "VaR cap exceeded",
        "rationale": intent.rationale,
    }


def _compute_portfolio_risk(positions: list[PositionItem], portfolio_value: float, settings) -> dict[str, Any]:
    dd_limit = float(os.environ.get("GTP_MAX_DRAWDOWN_PCT", "10"))
    if positions:
        syms = [_yf_symbol(p.ticker) for p in positions]
        try:
            data = yf.download(syms, period="6mo", interval="1d", progress=False)["Close"]
            if hasattr(data, "columns") and len(data.columns) == 1:
                weights = np.array([1.0])
                rets = data.pct_change().dropna()
            else:
                weights = np.ones(len(syms)) / len(syms)
                rets = data.pct_change().dropna().dot(weights)
            var_95 = float(np.percentile(rets.dropna(), 5) * portfolio_value) if len(rets) > 20 else 0.0
            sharpe = float(rets.mean() / rets.std() * np.sqrt(252)) if rets.std() > 0 else 0.0
            equity = (1 + rets).cumprod()
            max_dd = float(((equity - equity.cummax()) / equity.cummax()).min() * 100)
        except Exception:
            var_95, sharpe, max_dd = 0.0, 0.0, 0.0
    else:
        try:
            rets = yf.Ticker("SPY").history(period="6mo")["Close"].pct_change().dropna()
            var_95 = float(np.percentile(rets, 5) * portfolio_value)
            sharpe = float(rets.mean() / rets.std() * np.sqrt(252)) if rets.std() > 0 else 0.0
            equity = (1 + rets).cumprod()
            max_dd = float(((equity - equity.cummax()) / equity.cummax()).min() * 100)
        except Exception:
            var_95, sharpe, max_dd = 0.0, 0.0, 0.0

    return {
        "var_95": round(var_95, 0),
        "sharpe": round(sharpe, 2),
        "max_dd": round(max_dd, 1),
        "dd_limit": dd_limit,
        "dd_pct_of_limit": min(100, int(abs(max_dd) / dd_limit * 100)) if dd_limit else 0,
        "sizing_model": "VaR-scaled",
    }


def _run_backtest(ticker: str) -> dict[str, Any]:
    end = datetime.now()
    start = end - timedelta(days=365)
    try:
        result = BacktestEngine(
            BacktestConfig(ticker=ticker, start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"))
        ).run("buy_hold")
        return {
            "ticker": ticker,
            "sharpe": round(result.sharpe_ratio, 2),
            "max_dd": round(result.max_drawdown * 100, 1),
            "win_rate": round(result.win_rate * 100, 0),
            "total_return": round(result.total_return * 100, 1),
        }
    except Exception:
        return {"ticker": ticker, "sharpe": 0.0, "max_dd": 0.0, "win_rate": 0.0, "total_return": 0.0}


def _build_workflows(macro, screen_passed: int, watchlist_len: int, execution: dict, settings) -> list[WorkflowItem]:
    macro_pill = macro.pill_text()
    kill = "Blocked" if settings.kill_switch else "Armed"
    exec_badge = "Running" if execution.get("gate_open") else "Paused"
    exec_class = "running" if execution.get("gate_open") else "idle"
    return [
        WorkflowItem(
            f"FRED macro → agents ({macro.regime})",
            macro_pill,
            "shield",
            "blue",
            "Active" if macro.source != "fallback" else "Fallback",
            "running" if macro.source != "fallback" else "sched",
        ),
        WorkflowItem(
            "Watchlist consensus screen",
            f"{screen_passed}/{watchlist_len} passed · min score 0.5",
            "robot",
            "green",
            "Complete",
            "running",
        ),
        WorkflowItem(
            f"VWAP → SOR · {execution.get('ticker', '—')}",
            execution.get("rationale", "")[:60],
            "chart",
            "amber",
            exec_badge,
            exec_class,
        ),
        WorkflowItem(
            "Risk gate + kill switch",
            f"{settings.max_daily_loss_base:,.0f} daily loss cap · kill switch {kill}",
            "shield",
            "blue",
            kill,
            "idle" if not settings.kill_switch else "sched",
        ),
    ]


def load_dashboard_state() -> Phase2DashboardState:
    """Build dashboard from live agents, broker, market data, and execution bridge."""
    settings = load_settings()
    watchlist = _env_watchlist()
    signal_ticker = _env_signal_ticker(watchlist)
    portfolio_value = _env_portfolio_value()
    macro = _load_macro()
    macro_pill = macro.pill_text()
    positions, broker_connected, account_cash, account_equity, broker_error = _load_broker_snapshot(settings)
    broker_mode = _broker_mode_label(settings, connected=broker_connected)
    if account_equity is not None and account_equity > 0:
        portfolio_value = account_equity

    pills: list[dict[str, str]] = []
    for label, sym in [("SPY", "SPY"), ("QQQ", "QQQ"), ("BTC", "BTC-USD"), ("VIX", "^VIX")]:
        try:
            hist = yf.Ticker(sym).history(period="5d")["Close"].dropna()
            if len(hist) >= 2:
                chg = (hist.iloc[-1] / hist.iloc[-2] - 1) * 100
                sign = "+" if chg >= 0 else ""
                cls = "up" if chg >= 0 else "down"
                if label == "VIX":
                    pills.append({"label": f"VIX {hist.iloc[-1]:.1f}", "class": ""})
                else:
                    pills.append({"label": f"{label} {sign}{chg:.2f}%", "class": cls})
        except Exception:
            pills.append({"label": label, "class": ""})

    consensus_result, screen_result, bridge_result = _run_async(
        _load_live_analysis(signal_ticker, watchlist, macro)
    )

    consensus = _consensus_strip_from_results(consensus_result.agent_results)
    passed_tickers = {r.ticker for r in screen_result.passed}
    agents = _agent_cards_from_consensus(
        consensus_result,
        watchlist,
        macro_pill,
        passed_tickers,
        len(watchlist),
    )
    execution = _compute_execution_pipeline(bridge_result, settings, portfolio_value)
    risk = _compute_portfolio_risk(positions, portfolio_value, settings)
    backtest = _run_backtest(signal_ticker)
    workflows = _build_workflows(macro, len(screen_result.passed), len(watchlist), execution, settings)

    tape_symbols = list(dict.fromkeys(TAPE_SYMBOLS + watchlist + [_yf_symbol(p.ticker) for p in positions]))
    news_symbols = list(dict.fromkeys(NEWS_SYMBOLS + watchlist))

    source_parts = [f"agents:{signal_ticker}", f"macro:{macro.source}", f"broker:{broker_mode}"]
    if account_equity is not None:
        source_parts.append(f"equity:${account_equity:,.0f}")
    elif broker_error:
        source_parts.append("ibkr:unavailable")
    now = datetime.now()

    return Phase2DashboardState(
        macro=macro,
        market_pills=pills,
        consensus=consensus,
        execution=execution,
        agents=agents,
        workflows=workflows,
        risk=risk,
        positions=positions,
        backtest=backtest,
        ticker_tape=fetch_ticker_tape(tape_symbols),
        news_items=fetch_market_news(news_symbols),
        ipo_suggestions=fetch_ipo_suggestions_sync(macro),
        timestamp=now.strftime("%H:%M ET"),
        signal_ticker=signal_ticker,
        watchlist=watchlist,
        broker_mode=broker_mode,
        broker_connected=broker_connected,
        account_cash=account_cash,
        account_equity=account_equity,
        portfolio_value=portfolio_value,
        broker_error=broker_error,
        data_source=" · ".join(source_parts),
    )
