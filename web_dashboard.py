#!/usr/bin/env python3
"""
Crosspoint Global Trading Platform — web dashboard.
Live agent consensus, execution pipeline, ticker tape, and slide-over charts.
"""

from __future__ import annotations

import os
import secrets
import sys
import threading

_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_ROOT, "src"))
os.chdir(_ROOT)

from global_trading.settings import load_settings

load_settings()

import dash
from dash import ALL, Input, Output, State, callback, ctx, dcc, html, no_update
from flask import redirect, render_template_string, request, session, url_for
import plotly.graph_objs as go
import yfinance as yf

from fincept_terminal.dashboard.phase2_state import (
    NEWS_SYMBOLS,
    TAPE_SYMBOLS,
    Phase2DashboardState,
    TickerTapeItem,
    fetch_market_news,
    fetch_ticker_tape,
    load_dashboard_state,
    placeholder_dashboard_state,
)
from global_trading.executor import run_workflow_once
from global_trading.core.domain import AssetClass
from global_trading.instruments import (
    analysis_ticker,
    apply_env_defaults,
    parse_instrument_token,
    watchlist_specs_from_env,
)

C = {
    "bg": "linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)",
    "card": "#2a2a4a",
    "card2": "#1f1f3a",
    "border": "#3a3a6a",
    "text": "#ffffff",
    "muted": "#b8b8d0",
    "dim": "#888888",
    "accent": "#00d4ff",
    "pos": "#00ff88",
    "neg": "#ff4757",
    "warn": "#ffb347",
    "purple": "#9b8cff",
}

PERIOD_MAP = {"1D": "1d", "5D": "5d", "1M": "1mo", "3M": "3mo"}

_STATE: Phase2DashboardState | None = None

_execute_job: dict = {"running": False, "result": None}


def _format_execute_message(result: dict | None) -> str:
    if not result:
        return "Workflow finished."
    if result.get("status") == "submitted" and result.get("order"):
        order = result["order"]
        sym = order.get("instrument", {}).get("symbol", result.get("ticker", ""))
        qty = order.get("quantity", "?")
        return f"Order submitted · {sym} · qty {qty} · broker {result.get('broker_mode', '')}"
    reason = result.get("skipped_reason") or "No order placed"
    return f"Trade skipped · {result.get('ticker', '')} · {reason}"


def _broker_status_label(state: Phase2DashboardState) -> tuple[str, str]:
    if state.broker_mode == "loading":
        return "LOADING", C["warn"]
    if state.broker_mode == "stub":
        return "SIMULATED · no IBKR account needed", C["pos"]
    if state.broker_connected and state.account_equity is not None:
        cash_note = f" · cash ${state.account_cash:,.0f}" if state.account_cash is not None else ""
        return f"{state.broker_mode.upper()} · ${state.account_equity:,.0f}{cash_note}", C["pos"]
    if state.broker_connected:
        return state.broker_mode.upper(), C["pos"]
    if state.broker_error:
        return "DISCONNECTED", C["warn"]
    return "DISCONNECTED", C["warn"]


_ASSET_CLASS_COLORS = {
    AssetClass.EQUITY: C["accent"],
    AssetClass.FUTURES: C["warn"],
    AssetClass.OPTION: C["purple"],
    AssetClass.FX: C["pos"],
    AssetClass.CRYPTO: C["neg"],
}


def _tradeable_universe_panel() -> html.Div:
    """Show configured instruments and whether orders are simulated or IBKR-routed."""
    settings = load_settings()
    specs = watchlist_specs_from_env()
    simulated = settings.ibkr_use_stub
    if simulated:
        banner = (
            "Simulated broker — no IBKR account required. "
            "Agents, macro, and risk run live; orders stay in-app until you connect IBKR."
        )
        banner_class = "tu-banner"
        route_label = "Simulated"
        route_color = C["pos"]
    else:
        banner = (
            "IBKR paper mode — requires a free IBKR paper account + Gateway on port 7497. "
            "Sign up at interactivebrokers.com (Paper Trading is free)."
        )
        banner_class = "tu-banner-warn"
        route_label = "IBKR paper"
        route_color = C["accent"]

    header = html.Div(
        [
            html.Span("Instrument", className="tu-h"),
            html.Span("Class", className="tu-h"),
            html.Span("Agent data", className="tu-h"),
            html.Span("Orders", className="tu-h"),
        ],
        className="tu-header",
    )
    rows = [header]
    for spec in specs:
        ac_color = _ASSET_CLASS_COLORS.get(spec.asset_class, C["muted"])
        rows.append(
            html.Div(
                [
                    html.Span(spec.symbol, className="tu-symbol"),
                    html.Span(
                        spec.asset_class.value.upper(),
                        className="tu-class",
                        style={"color": ac_color},
                    ),
                    html.Span(analysis_ticker(spec), className="tu-data"),
                    html.Span(route_label, className="tu-route", style={"color": route_color}),
                ],
                className="tu-row",
            )
        )
    enabled = ", ".join(sorted({s.asset_class.value for s in specs}))
    return html.Div(
        [
            html.Div(banner, className=banner_class),
            html.Div(f"Enabled asset classes: {enabled}", className="tu-sub"),
            html.Div(rows, className="tu-list"),
        ],
        className="tradeable-universe",
        id="tradeable-universe",
    )


def _account_summary(state: Phase2DashboardState) -> list:
    if state.broker_mode == "stub":
        return [
            html.Div(
                f"Portfolio (config): ${state.portfolio_value:,.0f} · simulated broker",
                className="account-line",
            )
        ]
    if state.broker_connected and state.account_equity is not None:
        lines = [
            html.Div(f"Net liquidation: ${state.account_equity:,.0f}", className="account-line"),
        ]
        if state.account_cash is not None:
            lines.append(html.Div(f"Cash: ${state.account_cash:,.0f}", className="account-line dim"))
        return lines
    msg = "IBKR not connected — set GTP_IBKR_USE_STUB=1 in .env to trade without an IBKR account"
    if state.broker_error:
        msg = f"IBKR unavailable — {state.broker_error[:80]}"
    return [html.Div(msg, className="account-line warn")]


def _toast_style(ok: bool) -> dict:
    border = C["pos"] if ok else C["warn"]
    return {
        "display": "block",
        "position": "fixed",
        "bottom": "60px",
        "right": "20px",
        "background": C["card"],
        "border": f"1px solid {border}",
        "padding": "12px 16px",
        "borderRadius": "8px",
        "fontSize": "12px",
        "maxWidth": "360px",
        "zIndex": 1000,
    }


def get_state() -> Phase2DashboardState:
    global _STATE
    if _STATE is None:
        _STATE = placeholder_dashboard_state()
    return _STATE


def set_state(state: Phase2DashboardState) -> None:
    global _STATE
    _STATE = state


def _yf_symbol(ticker: str) -> str:
    return ticker.replace("/", "-")


_chart_btn_seq = 0


def _chart_btn_id(ticker: str) -> dict:
    """Unique pattern ID — Dash rejects duplicate ids across buttons."""
    global _chart_btn_seq
    _chart_btn_seq += 1
    return {"type": "open-chart", "ticker": _yf_symbol(ticker), "index": _chart_btn_seq}


app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "Crosspoint Global Trading Platform"


def _dashboard_auth_enabled() -> bool:
    return os.environ.get("GTP_DASHBOARD_AUTH_ENABLED", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _dashboard_credentials() -> tuple[str, str]:
    return (
        os.environ.get("GTP_DASHBOARD_USER", "").strip(),
        os.environ.get("GTP_DASHBOARD_PASSWORD", "").strip(),
    )


def _dashboard_auth_ok(username: str, password_attempt: str) -> bool:
    user, password = _dashboard_credentials()
    if not user or not password:
        return False
    return secrets.compare_digest(username, user) and secrets.compare_digest(
        password_attempt, password
    )


_LOGIN_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Crosspoint Login</title>
  <style>
    body { margin: 0; min-height: 100vh; display: grid; place-items: center;
      background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
      font-family: Segoe UI, Arial, sans-serif; color: #fff; }
    .card { width: min(92vw, 380px); background: #2a2a4a; border: 1px solid #3a3a6a;
      border-radius: 12px; padding: 28px; box-shadow: 0 12px 40px rgba(0,0,0,.35); }
    h1 { margin: 0 0 6px; font-size: 1.35rem; color: #00d4ff; }
    p { margin: 0 0 20px; color: #b8b8d0; font-size: .92rem; }
    label { display: block; margin-bottom: 6px; color: #b8b8d0; font-size: .85rem; }
    input { width: 100%; box-sizing: border-box; margin-bottom: 14px; padding: 10px 12px;
      border-radius: 8px; border: 1px solid #3a3a6a; background: #1f1f3a; color: #fff; }
    button { width: 100%; padding: 11px; border: 0; border-radius: 8px; cursor: pointer;
      background: #00d4ff; color: #0f172a; font-weight: 700; }
    .err { margin-bottom: 12px; color: #ff4757; font-size: .88rem; }
  </style>
</head>
<body>
  <form class="card" method="post" action="{{ action }}">
    <h1>Crosspoint Global Trading</h1>
    <p>Sign in to view the dashboard.</p>
    {% if error %}<div class="err">{{ error }}</div>{% endif %}
    <label for="username">Username</label>
    <input id="username" name="username" autocomplete="username" required />
    <label for="password">Password</label>
    <input id="password" name="password" type="password" autocomplete="current-password" required />
    <button type="submit">Sign in</button>
  </form>
</body>
</html>"""


def _configure_dashboard_auth() -> None:
    secret = os.environ.get("GTP_DASHBOARD_SECRET", "").strip()
    if not secret:
        _, password = _dashboard_credentials()
        secret = password or "crosspoint-dev-secret"
    app.server.secret_key = secret


_configure_dashboard_auth()
app.server.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=False,
)


@app.server.route("/login", methods=["GET", "POST"])
def _dashboard_login():
    if not _dashboard_auth_enabled():
        return redirect("/")
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password_attempt = request.form.get("password") or ""
        if _dashboard_auth_ok(username, password_attempt):
            session["dashboard_authenticated"] = True
            return redirect("/")
        return render_template_string(
            _LOGIN_PAGE,
            action=url_for("_dashboard_login"),
            error="Invalid username or password.",
        )
    if session.get("dashboard_authenticated"):
        return redirect("/")
    return render_template_string(_LOGIN_PAGE, action=url_for("_dashboard_login"), error=None)


@app.server.route("/logout", methods=["GET", "POST"])
def _dashboard_logout():
    session.pop("dashboard_authenticated", None)
    return redirect(url_for("_dashboard_login"))


@app.server.before_request
def _protect_dashboard():
    if not _dashboard_auth_enabled():
        return None
    if request.path in ("/login", "/logout"):
        return None
    if session.get("dashboard_authenticated"):
        return None
    auth = request.authorization
    if auth and _dashboard_auth_ok(auth.username or "", auth.password or ""):
        session["dashboard_authenticated"] = True
        return None
    return redirect(url_for("_dashboard_login"))


def _section_label(text: str, badge: str | None = None) -> html.Div:
    children: list = [text]
    if badge:
        children.append(
            html.Span(badge, className="p2-badge", style={"marginLeft": "6px"})
        )
    return html.Div(children, className="section-label")


def _brand_lockup() -> html.Div:
    return html.Div(
        [
            html.Img(
                src=app.get_asset_url("android-chrome-192x192.png"),
                className="brand-logo",
                alt="Crosspoint logo",
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.Span("Cross", className="brand-cross"),
                            html.Span("point", className="brand-point"),
                        ],
                        className="brand-name",
                    ),
                    html.Div("Global Trading Platform", className="brand-sub"),
                ],
                className="brand-text",
            ),
        ],
        className="brand-lockup",
    )


def _load_ohlc_figure(ticker: str, period_key: str = "1M") -> go.Figure:
    sym = _yf_symbol(ticker)
    period = PERIOD_MAP.get(period_key, "1mo")
    try:
        hist = yf.Ticker(sym).history(period=period)
        if hist.empty:
            raise ValueError("no data")
        positive = float(hist["Close"].iloc[-1]) >= float(hist["Close"].iloc[0])
        color = C["pos"] if positive else C["neg"]
        fig = go.Figure(
            data=[
                go.Candlestick(
                    x=hist.index,
                    open=hist["Open"],
                    high=hist["High"],
                    low=hist["Low"],
                    close=hist["Close"],
                    increasing_line_color=C["pos"],
                    decreasing_line_color=C["neg"],
                    name=sym,
                )
            ]
        )
        fig.update_layout(
            title=f"{sym} · {period_key}",
            template="plotly_dark",
            height=420,
            margin=dict(l=40, r=20, t=40, b=30),
            paper_bgcolor=C["card2"],
            plot_bgcolor=C["card2"],
            font=dict(color=C["text"], size=11),
            xaxis_rangeslider_visible=False,
            showlegend=False,
        )
        return fig
    except Exception as exc:
        return go.Figure(
            layout=dict(
                title=f"{sym} — chart unavailable ({exc})",
                template="plotly_dark",
                height=420,
                paper_bgcolor=C["card2"],
            )
        )


def _tape_symbols(state: Phase2DashboardState | None = None) -> list[str]:
    state = state or get_state()
    pos_syms = [_yf_symbol(p.ticker) for p in state.positions]
    return list(dict.fromkeys(TAPE_SYMBOLS + pos_syms))


def _news_symbols(state: Phase2DashboardState | None = None) -> list[str]:
    state = state or get_state()
    pos_syms = [_yf_symbol(p.ticker) for p in state.positions]
    return list(dict.fromkeys(NEWS_SYMBOLS + pos_syms))


def _format_tape_price(item: TickerTapeItem) -> str:
    if item.symbol.startswith("^"):
        return f"{item.price:.1f}"
    if item.price >= 1000:
        return f"${item.price:,.0f}"
    return f"${item.price:.2f}"


def _tape_chip(item: TickerTapeItem) -> html.Span:
    sign = "+" if item.change_pct >= 0 else ""
    cls = "tape-chip up" if item.change_pct >= 0 else "tape-chip down"
    return html.Span(
        [
            html.Span(item.label, className="tape-sym"),
            html.Span(_format_tape_price(item), className="tape-px"),
            html.Span(f"{sign}{item.change_pct:.2f}%", className="tape-chg"),
        ],
        className=cls,
    )


def _build_tape_children(items: list[TickerTapeItem]) -> list:
    chips = [_tape_chip(item) for item in items]
    if not chips:
        chips = [html.Span("Market data loading…", className="tape-chip flat")]
    return chips + chips


def _build_news_children(items) -> list:
    if not items:
        return [html.Div("Loading headlines…", className="news-empty")]
    rows = []
    for item in items:
        rows.append(
            html.A(
                [
                    html.Div(
                        [
                            html.Span(item.symbol, className="news-sym"),
                            html.Span(item.published, className="news-time"),
                        ],
                        className="news-meta",
                    ),
                    html.Div(item.title, className="news-title"),
                    html.Div(item.publisher, className="news-pub"),
                ],
                href=item.link or "#",
                target="_blank",
                rel="noopener noreferrer",
                className="news-row",
            )
        )
    return rows


def _ticker_tape_bar(state: Phase2DashboardState | None = None) -> html.Div:
    state = state or get_state()
    return html.Div(
        [
            html.Div("LIVE", className="ticker-tape-label"),
            html.Div(
                html.Div(
                    _build_tape_children(state.ticker_tape),
                    id="ticker-tape-track",
                    className="ticker-tape-track",
                ),
                className="ticker-tape-viewport",
            ),
        ],
        className="ticker-tape-wrap",
    )


def _ipo_status_class(status: str) -> str:
    return {"upcoming": "ipo-upcoming", "recent": "ipo-recent", "open": "ipo-open"}.get(status, "ipo-open")


def _ipo_opportunities(state: Phase2DashboardState | None = None) -> html.Div:
    state = state or get_state()
    cards = []
    for ipo in state.ipo_suggestions:
        agents = ", ".join(ipo.leading_agents) if ipo.leading_agents else "—"
        sym = ipo.ticker or "PRE-IPO"
        vote_tags = []
        for v in ipo.agent_votes:
            cls = f"ipo-vote {v.endorsement}"
            vote_tags.append(html.Span(v.agent[0], className=cls, title=f"{v.agent}: {v.rationale}"))
        chart_btn = []
        if ipo.ticker:
            chart_btn = [
                html.Button(
                    "📈",
                    id=_chart_btn_id(ipo.ticker),
                    className="chart-btn",
                    title=f"Open {ipo.ticker} chart",
                    n_clicks=0,
                )
            ]
        cards.append(
            html.Div(
                [
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Span(ipo.company, className="ipo-company"),
                                    html.Span(sym, className="ipo-ticker"),
                                ],
                                className="ipo-title-row",
                            ),
                            html.Span(ipo.status.upper(), className=f"ipo-status {_ipo_status_class(ipo.status)}"),
                        ],
                        className="ipo-header",
                    ),
                    html.Div(
                        [
                            html.Span(ipo.sector, className="ipo-sector"),
                            html.Span(ipo.est_window, className="ipo-window"),
                        ],
                        className="ipo-meta",
                    ),
                    html.Div(vote_tags, className="ipo-votes"),
                    html.Div(
                        [
                            html.Span(f"{ipo.composite_score:.2f}", className="ipo-score"),
                            html.Span(ipo.recommendation.replace("_", " "), className="ipo-rec"),
                        ],
                        className="ipo-score-row",
                    ),
                    html.Div(f"Led by {agents}", className="ipo-agents"),
                    html.Div(ipo.entry_note, className="ipo-note"),
                    html.Div(ipo.macro_fit, className="ipo-macro"),
                    html.Div(chart_btn, className="ipo-actions"),
                ],
                className="ipo-card",
            )
        )
    if not cards:
        cards = [html.Div("No IPO candidates meet agent thresholds.", className="ipo-empty")]
    return html.Div(
        [
            _section_label("IPO early entry", "Agent screen"),
            html.Div(cards, className="ipo-list"),
        ]
    )


def _news_feed(state: Phase2DashboardState | None = None) -> html.Div:
    state = state or get_state()
    return html.Div(
        [
            _section_label("Market news", "Yahoo Finance"),
            html.Div(_build_news_children(state.news_items), id="news-feed", className="news-list"),
        ]
    )


def _consensus_strip(state: Phase2DashboardState | None = None) -> html.Div:
    state = state or get_state()
    items = []
    for item in state.consensus:
        delta_cls = "cs-delta" if item.delta >= 0 else "cs-delta neg"
        delta_sign = "+" if item.delta >= 0 else ""
        items.append(
            html.Div(
                [
                    html.Div(item.name, className="cs-label"),
                    html.Div(
                        html.Div(
                            style={"width": f"{item.score * 100:.0f}%", "background": item.color},
                            className="cs-bar-fill",
                        ),
                        className="cs-bar-track",
                    ),
                    html.Div(
                        [
                            html.Div(f"{item.score:.2f}", className="cs-score"),
                            html.Div(f"{delta_sign}{item.delta:.2f}", className=delta_cls),
                        ],
                        style={"display": "flex", "alignItems": "baseline", "gap": "4px"},
                    ),
                ],
                className="cs-item",
            )
        )
    return html.Div(items, className="consensus-strip")


def _execution_block(state: Phase2DashboardState | None = None) -> html.Div:
    state = state or get_state()
    ex = state.execution
    route_steps = ex.get("route_steps") or ["Signal", "VaR gate", "Size", "SOR", "VWAP", "Fill"]
    active_steps = int(ex.get("active_steps", 1))
    steps = []
    for i, step in enumerate(route_steps):
        cls = "route-step route-active" if i < active_steps else "route-step"
        steps.append(html.Span(step, className=cls))
        if i < len(route_steps) - 1:
            steps.append(html.Span("→", className="route-arrow"))

    gate_open = ex.get("gate_open", False)
    gate_label = "Gate open" if gate_open else f"Gate closed · {ex.get('gate_reason', '')}"
    gate_color = C["pos"] if gate_open else C["warn"]

    return html.Div(
        [
            html.Div(
                [
                    html.Div("Smart order routing · VaR-gated", className="sor-title"),
                    html.Span(gate_label, style={"fontSize": "10px", "color": gate_color, "fontWeight": "500"}),
                ],
                className="sor-header",
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.Div("Algo", className="sor-cell-label"),
                            html.Div(ex.get("algo", "—"), className="sor-cell-val"),
                            html.Div(f"{ex.get('ticker', '—')} · {ex.get('raw_qty', 0)} shares", className="sor-cell-sub"),
                        ],
                        className="sor-cell",
                    ),
                    html.Div(
                        [
                            html.Div("Routed to", className="sor-cell-label"),
                            html.Div(ex.get("broker", "—"), className="sor-cell-val"),
                            html.Div(f"Score {ex.get('broker_score', 0):.2f} · best fill", className="sor-cell-sub"),
                        ],
                        className="sor-cell",
                    ),
                    html.Div(
                        [
                            html.Div("Slippage est.", className="sor-cell-label"),
                            html.Div(f"{ex.get('slippage_bps', 0):.1f} bps", className="sor-cell-val"),
                            html.Div(f"vs {ex.get('avg_slippage_bps', 0):.1f} bps avg", className="sor-cell-sub"),
                        ],
                        className="sor-cell",
                    ),
                ],
                className="sor-grid",
            ),
            html.Div(steps, className="sor-route"),
            html.Div(
                [
                    html.Span("Portfolio VaR post-trade", className="var-gate-label"),
                    html.Span(
                        f"−${abs(ex.get('post_trade_var', 0)):,.0f} < ${ex.get('var_cap', 0):,.0f} limit"
                        + (" ✓" if ex.get("var_ok") else " ✗"),
                        className="var-gate-val var-ok" if ex.get("var_ok") else "var-gate-val var-warn",
                    ),
                ],
                className="var-gate",
            ),
            html.Div(
                [
                    html.Span("Position size (VaR-scaled)", className="var-gate-label"),
                    html.Span(
                        f"{ex.get('raw_qty', 0)} shares → {ex.get('sized_qty', 0)} adjusted",
                        className="var-gate-val var-warn",
                    ),
                ],
                className="var-gate",
            ),
        ],
        className="sor-block",
    )


def _agent_cards(state: Phase2DashboardState | None = None) -> html.Div:
    state = state or get_state()
    cards = []
    for ag in state.agents:
        tags = []
        for t, active in ag["tickers"]:
            sym = _yf_symbol(t)
            tags.append(
                html.Button(
                    t,
                    id=_chart_btn_id(t),
                    className="ticker-tag active" if active else "ticker-tag",
                    title=f"Open {t} chart",
                    n_clicks=0,
                )
            )
        cards.append(
            html.Div(
                [
                    html.Div(
                        html.Div(
                            style={"width": f"{ag['score'] * 100:.0f}%", "background": ag["color"]},
                            className="conviction-fill",
                        ),
                        className="conviction-trace",
                    ),
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Div(ag["name"], className="agent-name"),
                                    html.Div(ag["strategy"], className="agent-strategy"),
                                ]
                            ),
                            html.Div(ag["signal"], className=f"agent-signal signal-{ag['signal_class']}"),
                        ],
                        className="agent-header",
                    ),
                    html.Div(tags, className="agent-tickers"),
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Div(f"{ag['score']:.2f}", className="agent-score-val"),
                                    html.Div("conviction", className="agent-score-label"),
                                ]
                            ),
                            html.Div(f"{ag['screened']} screened", className="agent-meta"),
                        ],
                        className="agent-score-row",
                    ),
                    html.Div(ag.get("macro_pill", ""), className="macro-pill") if ag.get("macro_pill") else None,
                ],
                className="agent-card",
            )
        )
    return html.Div(cards, className="agent-grid")


def _workflows(state: Phase2DashboardState | None = None) -> html.Div:
    state = state or get_state()
    icon_map = {"robot": "🤖", "chart": "📈", "shield": "🛡"}
    rows = []
    for wf in state.workflows:
        name_children: list = [wf.name]
        rows.append(
            html.Div(
                [
                    html.Div(icon_map.get(wf.icon, "•"), className=f"wf-icon {wf.icon_class}"),
                    html.Div(
                        [html.Div(name_children, className="wf-name"), html.Div(wf.meta, className="wf-meta")]
                    ),
                    html.Div(wf.badge, className=f"wf-badge badge-{wf.badge_class}"),
                ],
                className="wf-row",
            )
        )
    return html.Div(rows, className="workflow-list")


def _position_rows(state: Phase2DashboardState | None = None) -> list:
    state = state or get_state()
    rows = []
    for pos in state.positions:
        sym = _yf_symbol(pos.ticker)
        pnl_cls = "pos-pnl pos" if pos.pnl >= 0 else "pos-pnl neg"
        sign = "+" if pos.pnl >= 0 else ""
        rows.append(
            html.Div(
                [
                    html.Div(
                        [
                            html.Div(pos.ticker, className="pos-ticker"),
                            html.Div(f"{pos.side} · {pos.quantity}", className="pos-side"),
                        ],
                        className="pos-left",
                    ),
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Div(f"{sign}${abs(pos.pnl):,.0f}", className=pnl_cls),
                                    html.Div(f"{sign}{pos.pnl_pct:.1f}%", className="pos-pct"),
                                ],
                                style={"textAlign": "right"},
                            ),
                            html.Button(
                                "📈",
                                id=_chart_btn_id(pos.ticker),
                                className="chart-btn",
                                title="Price chart",
                                n_clicks=0,
                            ),
                        ],
                        className="pos-right",
                    ),
                ],
                className="pos-row",
            )
        )
    if not rows:
        state = state or get_state()
        if state.broker_error:
            hint = f"IBKR error: {state.broker_error[:100]}. Start Gateway on port 7497."
        elif not state.broker_connected:
            hint = "IBKR disconnected. Start TWS/IB Gateway (paper port 7497), then click Refresh."
        else:
            hint = "No open positions in your IBKR paper account yet."
        rows = [html.Div(hint, className="ipo-empty")]
    return rows


def _risk_panel(state: Phase2DashboardState | None = None) -> list:
    state = state or get_state()
    risk = state.risk
    return [
        html.Div(
            [
                html.Span("VaR (95%, 1d)"),
                html.Span(f"−${abs(risk['var_95']):,}", className="risk-val warn"),
            ],
            className="risk-row",
        ),
        html.Div(
            [
                html.Span("Sharpe (30d)"),
                html.Span(f"{risk['sharpe']:.2f}", className="risk-val ok"),
            ],
            className="risk-row",
        ),
        html.Div(
            [
                html.Span("Max drawdown"),
                html.Span(f"{risk['max_dd']:.1f}%", className="risk-val warn"),
            ],
            className="risk-row",
        ),
        html.Div(
            [
                html.Div(
                    [
                        html.Span("Drawdown vs limit", style={"fontSize": "10px", "color": C["dim"]}),
                        html.Span(
                            f"{abs(risk['max_dd']):.1f}% / {risk['dd_limit']:.0f}%",
                            style={"fontSize": "10px", "color": C["warn"]},
                        ),
                    ],
                    style={"display": "flex", "justifyContent": "space-between", "marginBottom": "3px"},
                ),
                html.Div(
                    html.Div(style={"width": f"{risk['dd_pct_of_limit']}%"}, className="drawdown-fill"),
                    className="drawdown-track",
                ),
            ]
        ),
        html.Div(
            [
                html.Span("Sizing model"),
                html.Span(risk["sizing_model"], className="risk-val ok"),
            ],
            className="risk-row",
        ),
    ]


def _backtest_metrics(state: Phase2DashboardState | None = None) -> html.Div:
    state = state or get_state()
    bt = state.backtest
    return html.Div(
        [
            html.Div(
                [
                    html.Div(f"{bt['sharpe']:.2f}", className="bt-val"),
                    html.Div("Sharpe", className="bt-label"),
                ],
                className="bt-card",
            ),
            html.Div(
                [
                    html.Div(f"{bt['max_dd']:.1f}%", className="bt-val", style={"color": C["neg"]}),
                    html.Div("Max DD", className="bt-label"),
                ],
                className="bt-card",
            ),
            html.Div(
                [
                    html.Div(f"{bt['win_rate']:.0f}%", className="bt-val", style={"color": C["pos"]}),
                    html.Div("Win rate", className="bt-label"),
                ],
                className="bt-card",
            ),
            html.Div(
                [
                    html.Div(f"{bt['total_return']:+.1f}%", className="bt-val"),
                    html.Div("Total return", className="bt-label"),
                ],
                className="bt-card",
            ),
        ],
        className="bt-metrics",
    )


def _chart_slideover() -> list:
    return [
        html.Div(id="slideover-backdrop", className="slideover-backdrop", n_clicks=0),
        html.Div(
            [
                html.Div(
                    [
                        html.Div(id="slideover-title", className="slideover-title"),
                        html.Button("×", id="slideover-close", className="slideover-close", n_clicks=0),
                    ],
                    className="slideover-header",
                ),
                html.Div(
                    dcc.Dropdown(
                        id="chart-period",
                        options=[
                            {"label": "1 Day", "value": "1D"},
                            {"label": "5 Days", "value": "5D"},
                            {"label": "1 Month", "value": "1M"},
                            {"label": "3 Months", "value": "3M"},
                        ],
                        value="1M",
                        clearable=False,
                        className="chart-period-select",
                    ),
                    className="slideover-controls",
                ),
                dcc.Graph(
                    id="slideover-chart",
                    config={"displayModeBar": False},
                    style={"height": "calc(100vh - 120px)"},
                ),
            ],
            id="chart-slideover",
            className="chart-slideover",
        ),
    ]


def create_layout():
    state = get_state()
    instrument_specs = watchlist_specs_from_env()
    pill_elems = [html.Span(p["label"], className=f"pill {p['class']}".strip()) for p in state.market_pills]
    broker_label, broker_color = _broker_status_label(state)

    dash_panel = html.Div(
        [
            html.Div(
                [
                    html.Div(
                        [
                            _brand_lockup(),
                            html.Div(pill_elems, className="market-pills"),
                        ],
                        className="topbar-left",
                    ),
                    html.Div(
                        [
                            html.Div(
                                className="live-dot",
                                style={"background": broker_color if state.broker_connected else C["warn"]},
                            ),
                            html.Span(broker_label, id="broker-status", className="live-label", style={"color": broker_color}),
                            html.Span(
                                id="status-timestamp",
                                children=state.timestamp,
                                style={"fontSize": "11px", "color": C["dim"], "marginLeft": "4px"},
                            ),
                        ],
                        className="status-row",
                    ),
                ],
                className="topbar",
            ),
            _ticker_tape_bar(state),
            html.Div(
                [
                    html.Div(
                        [
                            html.Div([_section_label("Agent consensus"), html.Div(id="consensus-strip", children=_consensus_strip(state))]),
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            _section_label("Execution pipeline"),
                                            html.Div(
                                                [
                                                    dcc.Dropdown(
                                                        id="execute-ticker",
                                                        options=[
                                                            {
                                                                "label": s.display,
                                                                "value": s.raw or s.symbol,
                                                            }
                                                            for s in instrument_specs
                                                        ],
                                                        value=state.signal_ticker,
                                                        clearable=False,
                                                        className="execute-ticker-dd",
                                                    ),
                                                    html.Span(
                                                        id="asset-class-badge",
                                                        children=next(
                                                            (
                                                                s.asset_class.value.upper()
                                                                for s in instrument_specs
                                                                if (s.raw or s.symbol) == state.signal_ticker
                                                            ),
                                                            "EQUITY",
                                                        ),
                                                        className="asset-class-badge",
                                                    ),
                                                    html.Button(
                                                        "Execute trade ▶",
                                                        id="execute-btn",
                                                        className="execute-btn-prominent",
                                                        n_clicks=0,
                                                        title="Run agents → risk → broker for selected ticker",
                                                    ),
                                                ],
                                                className="execute-row",
                                            ),
                                            html.Div(
                                                id="execute-hint",
                                                children="Select instrument above · Execute runs agents → risk → broker",
                                                className="execute-hint",
                                            ),
                                        ],
                                        className="section-row-with-action",
                                    ),
                                    html.Div(id="execution-block", children=_execution_block(state)),
                                ]
                            ),
                            html.Div([_section_label("Agent details"), html.Div(id="agent-cards", children=_agent_cards(state))]),
                            html.Div(
                                [
                                    html.Div([_section_label("Workflows")], className="workflow-header"),
                                    html.Div(id="workflow-list", children=_workflows(state)),
                                ]
                            ),
                            _news_feed(state),
                            html.Div(id="ipo-opportunities", children=_ipo_opportunities(state)),
                        ],
                        className="left",
                    ),
                    html.Div(
                        [
                            html.Div(
                                [
                                    _section_label("What you can trade"),
                                    _tradeable_universe_panel(),
                                ]
                            ),
                            html.Div(className="divider"),
                            html.Div(
                                [
                                    _section_label("Portfolio risk"),
                                    html.Div(id="risk-panel", children=_risk_panel(state)),
                                ]
                            ),
                            html.Div(className="divider"),
                            html.Div(
                                [
                                    _section_label("Open positions"),
                                    html.Div(id="account-summary", children=_account_summary(state), className="account-summary"),
                                    html.Div(_position_rows(state), id="pos-list", className="pos-list"),
                                ]
                            ),
                            html.Div(className="divider"),
                            html.Div(
                                [
                                    _section_label(f"Backtest · {state.backtest.get('ticker', state.signal_ticker)} buy-hold"),
                                    html.Div(id="backtest-metrics", children=_backtest_metrics(state)),
                                ]
                            ),
                        ],
                        className="right",
                    ),
                ],
                className="main",
            ),
            html.Div(
                [
                    html.Span(
                        id="footer-note",
                        children=f"Signal {state.signal_ticker} · {state.data_source}",
                        className="footer-note",
                    ),
                    html.Button("Refresh ↻", className="footer-btn", id="refresh-btn"),
                ],
                className="footer",
            ),
        ],
        className="dash",
    )

    return html.Div(
        [
            dcc.Store(id="chart-store", data=None),
            dcc.Interval(id="ticker-interval", interval=20_000, n_intervals=0),
            dcc.Interval(id="news-interval", interval=300_000, n_intervals=0),
            dcc.Interval(id="state-interval", interval=180_000, n_intervals=0),
            dcc.Interval(id="execute-poll", interval=2_000, n_intervals=0, disabled=True),
            dash_panel,
            html.Div(id="action-toast", style={"display": "none"}),
            *_chart_slideover(),
        ],
        className="app-root",
    )


CSS = f"""
body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: {C['bg']}; color: {C['text']}; margin: 0; padding: 16px; min-height: 100vh; }}
.app-root {{ max-width: 1200px; margin: 0 auto; position: relative; }}
.dash {{ background: {C['card2']}; border: 1px solid {C['border']}; border-radius: 10px; overflow: hidden; }}

.topbar {{ display:flex; align-items:center; justify-content:space-between; padding:10px 16px; border-bottom:1px solid {C['border']}; background:{C['card']}; }}
.topbar-left {{ display:flex; align-items:center; gap:14px; flex-wrap:wrap; }}
.brand-lockup {{ display:flex; align-items:center; gap:10px; }}
.brand-logo {{ width:36px; height:36px; border-radius:8px; box-shadow: 0 2px 8px rgba(0,0,0,0.35); }}
.brand-name {{ font-size:16px; font-weight:700; letter-spacing:-0.4px; line-height:1.1; }}
.brand-cross {{ color:{C['text']}; }}
.brand-point {{ color:{C['accent']}; }}
.brand-sub {{ font-size:10px; color:{C['dim']}; margin-top:2px; }}
.market-pills {{ display:flex; gap:6px; flex-wrap:wrap; }}
.pill {{ font-size:11px; padding:3px 8px; border-radius:20px; border:1px solid {C['border']}; color:{C['muted']}; background:{C['card2']}; }}
.pill.up {{ color:{C['pos']}; border-color:{C['pos']}; }}
.pill.down {{ color:{C['neg']}; border-color:{C['neg']}; }}
.status-row {{ display:flex; align-items:center; gap:8px; }}
.live-dot {{ width:6px; height:6px; border-radius:50%; background:{C['pos']}; animation:pulse 2s ease-in-out infinite; }}
@keyframes pulse {{ 0%,100%{{opacity:1}} 50%{{opacity:.4}} }}
.live-label {{ font-size:11px; color:{C['pos']}; font-weight:500; max-width:280px; text-align:right; }}
.account-summary {{ margin-bottom:8px; }}
.account-line {{ font-size:11px; color:{C['text']}; margin-bottom:3px; }}
.account-line.dim {{ color:{C['dim']}; }}
.account-line.warn {{ color:{C['warn']}; font-size:10px; line-height:1.35; }}

.ticker-tape-wrap {{ display:flex; align-items:stretch; border-bottom:1px solid {C['border']}; background:{C['card']}; height:30px; overflow:hidden; }}
.ticker-tape-label {{ flex-shrink:0; display:flex; align-items:center; padding:0 12px; font-size:10px; font-weight:700; letter-spacing:.06em; color:{C['accent']}; border-right:1px solid {C['border']}; background:{C['card2']}; }}
.ticker-tape-viewport {{ flex:1; overflow:hidden; position:relative; }}
.ticker-tape-track {{ display:inline-flex; align-items:center; gap:18px; padding:0 14px; height:30px; white-space:nowrap; animation:ticker-scroll 45s linear infinite; }}
.ticker-tape-track:hover {{ animation-play-state:paused; }}
@keyframes ticker-scroll {{ 0%{{ transform:translateX(0); }} 100%{{ transform:translateX(-50%); }} }}
.tape-chip {{ display:inline-flex; align-items:center; gap:6px; font-size:11px; padding:2px 0; }}
.tape-chip.up .tape-chg {{ color:{C['pos']}; }}
.tape-chip.down .tape-chg {{ color:{C['neg']}; }}
.tape-chip.flat {{ color:{C['dim']}; }}
.tape-sym {{ font-weight:600; color:{C['text']}; }}
.tape-px {{ color:{C['muted']}; }}
.tape-chg {{ font-weight:600; font-size:10px; }}

.news-list {{ display:flex; flex-direction:column; gap:6px; max-height:220px; overflow-y:auto; }}
.news-row {{ display:block; background:{C['card']}; border:1px solid {C['border']}; border-radius:8px; padding:8px 10px; text-decoration:none; color:inherit; transition:border-color .15s ease; }}
.news-row:hover {{ border-color:{C['accent']}; }}
.news-meta {{ display:flex; align-items:center; justify-content:space-between; margin-bottom:4px; }}
.news-sym {{ font-size:10px; font-weight:600; color:{C['accent']}; }}
.news-time {{ font-size:10px; color:{C['dim']}; }}
.news-title {{ font-size:11px; font-weight:500; line-height:1.35; color:{C['text']}; }}
.news-pub {{ font-size:10px; color:{C['dim']}; margin-top:3px; }}
.news-empty {{ font-size:11px; color:{C['dim']}; padding:8px 2px; }}

.ipo-list {{ display:flex; flex-direction:column; gap:8px; max-height:360px; overflow-y:auto; }}
.ipo-card {{ background:{C['card']}; border:1px solid {C['border']}; border-radius:8px; padding:10px 12px; }}
.ipo-header {{ display:flex; align-items:flex-start; justify-content:space-between; margin-bottom:6px; }}
.ipo-title-row {{ display:flex; flex-direction:column; gap:2px; }}
.ipo-company {{ font-size:12px; font-weight:600; color:{C['text']}; }}
.ipo-ticker {{ font-size:10px; color:{C['accent']}; font-weight:600; }}
.ipo-status {{ font-size:9px; font-weight:700; padding:2px 6px; border-radius:3px; letter-spacing:.04em; }}
.ipo-upcoming {{ background:rgba(0,212,255,0.12); color:{C['accent']}; border:1px solid rgba(0,212,255,0.35); }}
.ipo-recent {{ background:rgba(255,179,71,0.12); color:{C['warn']}; border:1px solid rgba(255,179,71,0.35); }}
.ipo-open {{ background:rgba(0,255,136,0.12); color:{C['pos']}; border:1px solid rgba(0,255,136,0.35); }}
.ipo-meta {{ display:flex; gap:10px; font-size:10px; color:{C['dim']}; margin-bottom:6px; }}
.ipo-votes {{ display:flex; gap:4px; margin-bottom:6px; }}
.ipo-vote {{ width:18px; height:18px; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-size:9px; font-weight:700; cursor:help; }}
.ipo-vote.strong {{ background:rgba(0,255,136,0.2); color:{C['pos']}; border:1px solid {C['pos']}; }}
.ipo-vote.watch {{ background:rgba(255,179,71,0.15); color:{C['warn']}; border:1px solid {C['warn']}; }}
.ipo-vote.pass {{ background:{C['card2']}; color:{C['dim']}; border:1px solid {C['border']}; }}
.ipo-score-row {{ display:flex; align-items:baseline; gap:8px; margin-bottom:4px; }}
.ipo-score {{ font-size:16px; font-weight:600; color:{C['accent']}; }}
.ipo-rec {{ font-size:10px; font-weight:600; color:{C['pos']}; }}
.ipo-agents {{ font-size:10px; color:{C['muted']}; margin-bottom:4px; }}
.ipo-note {{ font-size:10px; color:{C['text']}; line-height:1.4; margin-bottom:4px; }}
.ipo-macro {{ font-size:9px; color:{C['dim']}; }}
.ipo-actions {{ margin-top:4px; }}
.ipo-empty {{ font-size:11px; color:{C['dim']}; padding:8px 2px; }}

.main {{ display:grid; grid-template-columns:1fr 280px; }}
.left {{ padding:14px; display:flex; flex-direction:column; gap:12px; }}
.section-label {{ font-size:10px; font-weight:600; letter-spacing:.08em; text-transform:uppercase; color:{C['dim']}; margin-bottom:6px; display:flex; align-items:center; }}
.section-row-with-action {{ display:flex; align-items:center; justify-content:space-between; gap:10px; margin-bottom:6px; }}
.section-row-with-action .section-label {{ margin-bottom:0; }}
.execute-row {{ display:flex; gap:8px; align-items:center; flex-wrap:wrap; }}
.execute-ticker-dd {{ min-width:140px; font-size:12px; }}
.asset-class-badge {{ font-size:10px; font-weight:700; color:{C['accent']}; background:rgba(0,212,255,0.12); border:1px solid {C['accent']}; border-radius:4px; padding:4px 8px; }}
.tradeable-universe {{ font-size:11px; }}
.tu-banner {{ background:rgba(0,255,136,0.08); border:1px solid rgba(0,255,136,0.35); border-radius:8px; padding:10px 12px; margin-bottom:8px; line-height:1.45; color:{C['muted']}; }}
.tu-banner-warn {{ background:rgba(255,179,71,0.08); border:1px solid rgba(255,179,71,0.35); border-radius:8px; padding:10px 12px; margin-bottom:8px; line-height:1.45; color:{C['muted']}; }}
.tu-sub {{ font-size:10px; color:{C['dim']}; margin-bottom:8px; }}
.tu-list {{ display:flex; flex-direction:column; gap:4px; }}
.tu-header, .tu-row {{ display:grid; grid-template-columns:1.1fr 0.8fr 1fr 0.9fr; gap:6px; align-items:center; padding:6px 8px; }}
.tu-header {{ color:{C['dim']}; font-size:9px; text-transform:uppercase; letter-spacing:0.04em; border-bottom:1px solid {C['border']}; }}
.tu-row {{ background:{C['card']}; border-radius:6px; border:1px solid {C['border']}; }}
.tu-symbol {{ font-weight:600; }}
.tu-class {{ font-weight:700; font-size:10px; }}
.tu-data {{ color:{C['dim']}; font-size:10px; }}
.tu-route {{ font-size:10px; font-weight:600; }}
.execute-hint {{ font-size:10px; color:{C['dim']}; margin-top:6px; }}
.execute-btn-prominent {{ font-size:12px; font-weight:600; color:{C['accent']}; background:rgba(0,212,255,0.12); border:1px solid {C['accent']}; border-radius:6px; padding:6px 14px; cursor:pointer; white-space:nowrap; }}
.execute-btn-prominent:hover {{ background:rgba(0,212,255,0.22); }}
.execute-btn-prominent:disabled {{ opacity:0.45; cursor:not-allowed; }}

.consensus-strip {{ background:{C['card']}; border:1px solid {C['border']}; border-radius:8px; padding:10px 14px; display:grid; grid-template-columns:repeat(4,1fr); gap:8px; }}
.cs-label {{ font-size:10px; color:{C['dim']}; }}
.cs-bar-track {{ height:4px; border-radius:2px; background:{C['border']}; overflow:hidden; margin:4px 0; }}
.cs-bar-fill {{ height:100%; border-radius:2px; }}
.cs-score {{ font-size:14px; font-weight:600; }}
.cs-delta {{ font-size:10px; color:{C['pos']}; }}
.cs-delta.neg {{ color:{C['neg']}; }}

.sor-block {{ background:{C['card']}; border:1px solid {C['border']}; border-radius:8px; padding:10px 12px; }}
.sor-header {{ display:flex; align-items:center; justify-content:space-between; margin-bottom:8px; }}
.sor-title {{ font-size:12px; font-weight:600; }}
.sor-grid {{ display:grid; grid-template-columns:repeat(3,1fr); gap:6px; }}
.sor-cell {{ background:{C['card2']}; border:1px solid {C['border']}; border-radius:8px; padding:7px 8px; }}
.sor-cell-label {{ font-size:10px; color:{C['dim']}; }}
.sor-cell-val {{ font-size:13px; font-weight:600; margin-top:2px; color:{C['accent']}; }}
.sor-cell-sub {{ font-size:10px; color:{C['dim']}; margin-top:1px; }}
.sor-route {{ display:flex; align-items:center; gap:6px; margin-top:8px; padding-top:8px; border-top:1px solid {C['border']}; flex-wrap:wrap; }}
.route-step {{ font-size:11px; color:{C['muted']}; }}
.route-arrow {{ font-size:10px; color:{C['dim']}; }}
.route-active {{ color:{C['pos']}; font-weight:600; }}
.var-gate {{ display:flex; align-items:center; justify-content:space-between; margin-top:6px; }}
.var-gate-label {{ font-size:11px; color:{C['muted']}; }}
.var-gate-val {{ font-size:11px; font-weight:600; }}
.var-ok {{ color:{C['pos']}; }}
.var-warn {{ color:{C['warn']}; }}

.p2-badge {{ font-size:9px; font-weight:600; padding:1px 5px; border-radius:3px; background:rgba(0,212,255,0.12); color:{C['accent']}; border:1px solid rgba(0,212,255,0.3); }}

.agent-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:8px; }}
.agent-card {{ background:{C['card2']}; border:1px solid {C['border']}; border-radius:8px; padding:12px; position:relative; overflow:hidden; }}
.conviction-trace {{ position:absolute; top:0; left:0; right:0; height:2px; background:{C['border']}; }}
.conviction-fill {{ height:100%; }}
.agent-header {{ display:flex; justify-content:space-between; margin-top:6px; }}
.agent-name {{ font-size:12px; font-weight:600; }}
.agent-strategy {{ font-size:10px; color:{C['dim']}; }}
.agent-signal {{ font-size:10px; font-weight:600; padding:2px 6px; border-radius:3px; }}
.signal-buy {{ background:rgba(0,255,136,0.12); color:{C['pos']}; }}
.signal-hold {{ background:rgba(255,179,71,0.12); color:{C['warn']}; }}
.agent-tickers {{ display:flex; gap:4px; margin-top:8px; flex-wrap:wrap; }}
.ticker-tag {{ font-size:10px; padding:2px 5px; border-radius:3px; border:1px solid {C['border']}; color:{C['muted']}; background:transparent; cursor:pointer; font-family:inherit; }}
.ticker-tag:hover {{ border-color:{C['accent']}; color:{C['accent']}; }}
.ticker-tag.active {{ border-color:{C['pos']}; color:{C['pos']}; background:rgba(0,255,136,0.07); }}
.agent-score-val {{ font-size:18px; font-weight:600; color:{C['accent']}; }}
.agent-score-label {{ font-size:10px; color:{C['dim']}; }}
.agent-meta {{ font-size:10px; color:{C['dim']}; }}
.macro-pill {{ font-size:10px; color:{C['accent']}; margin-top:6px; padding:3px 6px; border-radius:4px; background:rgba(0,212,255,0.08); border:1px solid rgba(0,212,255,0.25); display:inline-block; }}

.workflow-header {{ display:flex; align-items:center; justify-content:space-between; margin-bottom:6px; }}
.wf-add-btn {{ font-size:11px; color:{C['muted']}; background:{C['card']}; border:1px solid {C['border']}; border-radius:6px; padding:3px 8px; cursor:pointer; }}
.workflow-list {{ display:flex; flex-direction:column; gap:6px; }}
.wf-row {{ background:{C['card']}; border:1px solid {C['border']}; border-radius:8px; padding:8px 10px; display:flex; align-items:center; gap:8px; }}
.wf-icon {{ width:24px; height:24px; border-radius:5px; display:flex; align-items:center; justify-content:center; font-size:12px; }}
.wf-icon.green {{ background:rgba(0,255,136,0.12); color:{C['pos']}; }}
.wf-icon.amber {{ background:rgba(255,179,71,0.12); color:{C['warn']}; }}
.wf-icon.blue {{ background:rgba(0,212,255,0.12); color:{C['accent']}; }}
.wf-name {{ font-size:12px; font-weight:600; }}
.wf-meta {{ font-size:10px; color:{C['dim']}; }}
.wf-badge {{ margin-left:auto; font-size:10px; padding:2px 6px; border-radius:3px; font-weight:600; }}
.badge-running {{ background:rgba(0,255,136,0.12); color:{C['pos']}; }}
.badge-sched {{ background:rgba(255,179,71,0.12); color:{C['warn']}; }}
.badge-idle {{ background:{C['card2']}; color:{C['dim']}; border:1px solid {C['border']}; }}

.right {{ border-left:1px solid {C['border']}; padding:14px 12px; display:flex; flex-direction:column; gap:14px; }}
.divider {{ height:1px; background:{C['border']}; }}
.risk-row {{ display:flex; justify-content:space-between; margin-bottom:5px; font-size:12px; }}
.risk-val.warn {{ color:{C['warn']}; }}
.risk-val.ok {{ color:{C['pos']}; }}
.drawdown-track {{ height:5px; background:{C['border']}; border-radius:3px; overflow:hidden; margin-bottom:6px; }}
.drawdown-fill {{ height:100%; background:{C['warn']}; border-radius:3px; }}

.pos-row {{ display:flex; align-items:center; justify-content:space-between; padding:6px 0; border-bottom:1px solid {C['border']}; }}
.pos-left {{ flex:1; }}
.pos-ticker {{ font-size:12px; font-weight:600; }}
.pos-side {{ font-size:10px; color:{C['dim']}; }}
.pos-right {{ display:flex; align-items:center; gap:6px; }}
.pos-pnl.pos {{ color:{C['pos']}; font-weight:600; font-size:12px; }}
.pos-pnl.neg {{ color:{C['neg']}; font-weight:600; font-size:12px; }}
.pos-pct {{ font-size:10px; color:{C['dim']}; text-align:right; }}
.chart-btn {{ width:22px; height:22px; border-radius:4px; border:1px solid {C['border']}; background:{C['card']}; cursor:pointer; font-size:11px; color:{C['dim']}; padding:0; }}
.chart-btn:hover {{ border-color:{C['accent']}; color:{C['accent']}; background:rgba(0,212,255,0.08); }}

/* Slide-over chart panel — no layout shift */
.slideover-backdrop {{ position:fixed; inset:0; background:rgba(0,0,0,0.55); opacity:0; pointer-events:none; transition:opacity .3s ease; z-index:1998; }}
.slideover-backdrop.open {{ opacity:1; pointer-events:auto; }}
.chart-slideover {{ position:fixed; top:0; right:0; width:min(520px, 92vw); height:100vh; background:{C['card']}; border-left:1px solid {C['border']}; box-shadow:-8px 0 32px rgba(0,0,0,0.45); transform:translateX(100%); transition:transform .35s cubic-bezier(.4,0,.2,1); z-index:1999; display:flex; flex-direction:column; padding:16px; }}
.chart-slideover.open {{ transform:translateX(0); }}
.slideover-header {{ display:flex; align-items:center; justify-content:space-between; margin-bottom:10px; }}
.slideover-title {{ font-size:14px; font-weight:600; color:{C['accent']}; }}
.slideover-close {{ background:transparent; border:none; color:{C['dim']}; font-size:22px; cursor:pointer; line-height:1; padding:0 4px; }}
.slideover-close:hover {{ color:{C['text']}; }}
.slideover-controls {{ margin-bottom:8px; }}

.bt-metrics {{ display:grid; grid-template-columns:1fr 1fr; gap:6px; }}
.bt-card {{ background:{C['card']}; border-radius:8px; padding:8px 10px; }}
.bt-val {{ font-size:16px; font-weight:600; color:{C['accent']}; }}
.bt-label {{ font-size:10px; color:{C['dim']}; }}

.footer {{ padding:8px 16px; border-top:1px solid {C['border']}; background:{C['card']}; display:flex; align-items:center; justify-content:space-between; }}
.footer-note {{ font-size:10px; color:{C['dim']}; }}
.footer-btn {{ font-size:11px; color:{C['pos']}; background:rgba(0,255,136,0.08); border:1px solid {C['pos']}; border-radius:6px; padding:4px 10px; cursor:pointer; }}

@media (max-width: 900px) {{
  .main {{ grid-template-columns: 1fr; }}
  .right {{ border-left: none; border-top: 1px solid {C['border']}; }}
  .consensus-strip {{ grid-template-columns: repeat(2, 1fr); }}
  .agent-grid {{ grid-template-columns: 1fr; }}
}}
"""

app.index_string = f"""<!DOCTYPE html>
<html><head>{{%metas%}}
<title>Crosspoint Global Trading Platform</title>
<link rel="icon" type="image/x-icon" href="/assets/favicon.ico">
<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">
{{%css%}}
<style>{CSS}</style>
</head><body>{{%app_entry%}}{{%config%}}{{%scripts%}}{{%renderer%}}</body></html>"""


@callback(
    Output("chart-store", "data"),
    Input({"type": "open-chart", "ticker": ALL, "index": ALL}, "n_clicks"),
    Input("slideover-close", "n_clicks"),
    Input("slideover-backdrop", "n_clicks"),
    State("chart-store", "data"),
    prevent_initial_call=True,
)
def open_chart_panel(_btn_clicks, _close, _backdrop, current):
    if not ctx.triggered:
        return no_update
    trigger = ctx.triggered_id
    if trigger in ("slideover-close", "slideover-backdrop"):
        if ctx.triggered[0]["value"]:
            return None
        return no_update
    if isinstance(trigger, dict) and trigger.get("type") == "open-chart":
        if not ctx.triggered[0]["value"]:
            return no_update
        ticker = trigger["ticker"]
        return {"ticker": ticker, "period": (current or {}).get("period", "1M")}
    return no_update


@callback(
    Output("chart-slideover", "className"),
    Output("slideover-backdrop", "className"),
    Output("slideover-title", "children"),
    Input("chart-store", "data"),
)
def slideover_visibility(store):
    if store and store.get("ticker"):
        title = f"{store['ticker']} · Price action"
        return "chart-slideover open", "slideover-backdrop open", title
    return "chart-slideover", "slideover-backdrop", ""


@callback(
    Output("slideover-chart", "figure"),
    Input("chart-store", "data"),
    Input("chart-period", "value"),
)
def update_slideover_chart(store, period):
    if not store or not store.get("ticker"):
        return go.Figure(layout=dict(template="plotly_dark", paper_bgcolor=C["card2"]))
    return _load_ohlc_figure(store["ticker"], period or "1M")


@callback(
    Output("ticker-tape-track", "children"),
    Input("ticker-interval", "n_intervals"),
)
def refresh_ticker_tape(_n):
    return _build_tape_children(fetch_ticker_tape(_tape_symbols(get_state())))


@callback(
    Output("news-feed", "children"),
    Input("news-interval", "n_intervals"),
)
def refresh_news_feed(_n):
    return _build_news_children(fetch_market_news(_news_symbols(get_state())))


@callback(
    Output("consensus-strip", "children"),
    Output("execution-block", "children"),
    Output("agent-cards", "children"),
    Output("workflow-list", "children"),
    Output("pos-list", "children"),
    Output("account-summary", "children"),
    Output("broker-status", "children"),
    Output("risk-panel", "children"),
    Output("backtest-metrics", "children"),
    Output("ipo-opportunities", "children"),
    Output("status-timestamp", "children"),
    Output("footer-note", "children"),
    Input("state-interval", "n_intervals"),
    Input("refresh-btn", "n_clicks"),
    prevent_initial_call=False,
)
def refresh_live_state(_interval, _btn):
    state = load_dashboard_state()
    set_state(state)
    return (
        _consensus_strip(state),
        _execution_block(state),
        _agent_cards(state),
        _workflows(state),
        _position_rows(state),
        _account_summary(state),
        _broker_status_label(state)[0],
        _risk_panel(state),
        _backtest_metrics(state),
        _ipo_opportunities(state),
        state.timestamp,
        f"Signal {state.signal_ticker} · {state.data_source}",
    )


@callback(
    Output("asset-class-badge", "children"),
    Output("execute-hint", "children"),
    Input("execute-ticker", "value"),
)
def update_asset_badge(ticker: str | None):
    spec = apply_env_defaults(parse_instrument_token(ticker or "AAPL"))
    settings = load_settings()
    route = "simulated in-app" if settings.ibkr_use_stub else "IBKR paper (Gateway)"
    hint = f"{spec.display} · agents score via {analysis_ticker(spec)} · orders → {route}"
    return spec.asset_class.value.upper(), hint


@callback(
    Output("action-toast", "children"),
    Output("action-toast", "style"),
    Input("refresh-btn", "n_clicks"),
    prevent_initial_call=True,
)
def refresh_toast(_n):
    state = get_state()
    return (
        f"Refreshed · regime: {state.macro.regime} · {state.macro.pill_text()} · broker: {state.broker_mode}",
        _toast_style(True),
    )


@callback(
    Output("execute-poll", "disabled"),
    Output("execute-btn", "disabled"),
    Output("action-toast", "children", allow_duplicate=True),
    Output("action-toast", "style", allow_duplicate=True),
    Input("execute-btn", "n_clicks"),
    State("execute-ticker", "value"),
    prevent_initial_call=True,
)
def start_execute(_n, selected_ticker):
    if _execute_job["running"]:
        return no_update, True, no_update, no_update

    state = get_state()
    settings = load_settings()
    use_ibkr = not settings.ibkr_use_stub
    ticker = (selected_ticker or state.signal_ticker or "AAPL").strip()

    def _worker() -> None:
        try:
            _execute_job["result"] = run_workflow_once(ticker=ticker, use_ibkr=use_ibkr)
        except Exception as exc:
            _execute_job["result"] = {
                "status": "error",
                "ticker": ticker,
                "skipped_reason": str(exc),
            }
        finally:
            _execute_job["running"] = False

    _execute_job["running"] = True
    _execute_job["result"] = None
    threading.Thread(target=_worker, daemon=True).start()

    mode = "IBKR" if use_ibkr else "simulated"
    return (
        False,
        True,
        f"Running workflow · {ticker} · {mode}… (30–90s)",
        _toast_style(True),
    )


@callback(
    Output("execute-poll", "disabled", allow_duplicate=True),
    Output("execute-btn", "disabled", allow_duplicate=True),
    Output("action-toast", "children", allow_duplicate=True),
    Output("action-toast", "style", allow_duplicate=True),
    Output("consensus-strip", "children", allow_duplicate=True),
    Output("execution-block", "children", allow_duplicate=True),
    Output("pos-list", "children", allow_duplicate=True),
    Output("account-summary", "children", allow_duplicate=True),
    Output("broker-status", "children", allow_duplicate=True),
    Output("footer-note", "children", allow_duplicate=True),
    Input("execute-poll", "n_intervals"),
    prevent_initial_call=True,
)
def poll_execute(_n):
    if _execute_job["running"]:
        return (no_update,) * 10

    result = _execute_job.get("result")
    if result is None:
        return (no_update,) * 10

    ok = result.get("status") == "submitted"
    message = _format_execute_message(result)

    state = load_dashboard_state()
    set_state(state)

    _execute_job["result"] = None
    return (
        True,
        False,
        message,
        _toast_style(ok),
        _consensus_strip(state),
        _execution_block(state),
        _position_rows(state),
        _account_summary(state),
        _broker_status_label(state)[0],
        f"Signal {state.signal_ticker} · {state.data_source}",
    )


app.layout = create_layout

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8050"))
    host = os.environ.get("HOST", "127.0.0.1")
    debug = os.environ.get("DASH_DEBUG", "1").strip().lower() in ("1", "true", "yes")
    # Cloud hosts (Railway, Render, etc.) inject PORT and require 0.0.0.0
    if os.environ.get("PORT") or os.environ.get("RAILWAY_ENVIRONMENT"):
        host = "0.0.0.0"
        debug = False
    print("Starting Crosspoint Global Trading Platform")
    print(f"Open http://{host}:{port}")
    if _dashboard_auth_enabled():
        user, _ = _dashboard_credentials()
        print(f"Dashboard login enabled for user: {user or '(set GTP_DASHBOARD_USER)'}")
    app.run(debug=debug, host=host, port=port, use_reloader=False)
