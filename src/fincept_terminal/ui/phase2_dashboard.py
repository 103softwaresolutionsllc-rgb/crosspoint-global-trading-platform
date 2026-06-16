"""
Qt dashboard — live agent consensus, execution pipeline, and slide-over charts.
"""

from __future__ import annotations

from PyQt6.QtCore import QThread, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from fincept_terminal.dashboard.phase2_state import (
    Phase2DashboardState,
    TAPE_SYMBOLS,
    fetch_market_news,
    fetch_ticker_tape,
    load_dashboard_state,
)
from .chart_slideover import ChartSlideoverDialog, brand_logo_path
from .ticker_banner import LiveTickerBanner


class _StateLoaderThread(QThread):
    loaded = pyqtSignal(object)
    failed = pyqtSignal(str)

    def run(self) -> None:
        try:
            self.loaded.emit(load_dashboard_state())
        except Exception as exc:
            self.failed.emit(str(exc))


class Phase2DashboardWidget(QWidget):
    """Main trading dashboard for Qt6."""

    state_refreshed = pyqtSignal(object)

    def __init__(self, state: Phase2DashboardState | None = None, data_feed=None):
        super().__init__()
        self.state = state
        self._chart_btn_seq = 0
        self.data_feed = data_feed
        self._refreshing = False
        self._loader_thread: _StateLoaderThread | None = None
        self._scroll: QScrollArea | None = None
        self._status_label: QLabel | None = None
        self._refresh_btn: QPushButton | None = None
        self._build_shell()
        self._wire_data_feed()
        if self.state is not None:
            self._populate_body()
            self._apply_tape_and_news()
            self._update_status_label()
        else:
            self._show_loading()
            QTimer.singleShot(100, self.start_refresh)
        self._state_timer = QTimer(self)
        self._state_timer.timeout.connect(self.start_refresh)
        self._state_timer.start(180_000)
        self._tape_timer = QTimer(self)
        self._tape_timer.timeout.connect(self._refresh_tape_light)
        self._tape_timer.start(20_000)

    def _open_chart(self, ticker: str) -> None:
        ChartSlideoverDialog(ticker, self).exec()

    def _build_shell(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self._brand_bar())
        self.ticker_banner = LiveTickerBanner(self)
        root.addWidget(self.ticker_banner)
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet("QScrollArea { border: none; background: #1a1a2e; }")
        root.addWidget(self._scroll)

    def _show_loading(self) -> None:
        body = QWidget()
        body.setStyleSheet("background: #1a1a2e; color: white;")
        lay = QVBoxLayout(body)
        lbl = QLabel("Loading live market data and agent consensus…")
        lbl.setStyleSheet("color: #b8b8d0; padding: 24px; font-size: 13px;")
        lay.addWidget(lbl)
        lay.addStretch()
        self._scroll.setWidget(body)

    def _populate_body(self) -> None:
        body = QWidget()
        body.setStyleSheet("background: #1a1a2e; color: white;")
        grid = QHBoxLayout(body)

        left = QVBoxLayout()
        left.addWidget(self._section("Agent consensus"))
        left.addWidget(self._consensus_strip())
        left.addWidget(self._section("Execution pipeline"))
        left.addWidget(self._execution_block())
        left.addWidget(self._section("Agent details"))
        left.addLayout(self._agent_grid())
        left.addWidget(self._section("Workflows"))
        left.addLayout(self._workflows())
        left.addWidget(self._section("IPO early entry", badge="Agent screen"))
        left.addLayout(self._ipo_panel())
        left.addStretch()
        grid.addLayout(left, 3)

        right = QVBoxLayout()
        right.addWidget(self._section("Portfolio risk"))
        right.addLayout(self._risk_panel())
        right.addWidget(self._divider())
        right.addWidget(self._section("Open positions"))
        right.addLayout(self._positions())
        right.addWidget(self._divider())
        bt_ticker = self.state.backtest.get("ticker", self.state.signal_ticker)
        right.addWidget(self._section(f"Backtest · {bt_ticker} buy-hold"))
        right.addLayout(self._backtest_grid())
        right.addStretch()
        grid.addLayout(right, 1)

        old = self._scroll.takeWidget()
        if old is not None:
            old.deleteLater()
        self._scroll.setWidget(body)

    def _wire_data_feed(self) -> None:
        if self.data_feed is None:
            return
        self.data_feed.add_banner_callback(
            lambda sym, price, chg: self.ticker_banner.add_ticker_update(sym, price, chg)
        )

    def _brand_bar(self) -> QFrame:
        bar = QFrame()
        bar.setStyleSheet("background: #2a2a4a; border-bottom: 1px solid #3a3a6a; padding: 8px 12px;")
        lay = QHBoxLayout(bar)
        logo_path = brand_logo_path()
        if logo_path.exists():
            logo = QLabel()
            logo.setPixmap(QPixmap(str(logo_path)).scaled(36, 36, Qt.AspectRatioMode.KeepAspectRatio))
            lay.addWidget(logo)
        text = QVBoxLayout()
        title = QLabel("Crosspoint")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #00d4ff;")
        sub = QLabel("Global Trading Platform")
        sub.setStyleSheet("font-size: 10px; color: #888;")
        text.addWidget(title)
        text.addWidget(sub)
        lay.addLayout(text)
        lay.addStretch()
        self._status_label = QLabel("")
        self._status_label.setStyleSheet("font-size: 10px; color: #888;")
        lay.addWidget(self._status_label)
        self._refresh_btn = QPushButton("Refresh ↻")
        self._refresh_btn.setStyleSheet(
            "font-size: 11px; padding: 4px 10px; border: 1px solid #3a3a6a; border-radius: 4px; color: #00d4ff;"
        )
        self._refresh_btn.clicked.connect(self.start_refresh)
        lay.addWidget(self._refresh_btn)
        return bar

    def _update_status_label(self) -> None:
        if self._status_label is None or self.state is None:
            return
        self._status_label.setText(
            f"{self.state.broker_mode.upper()} · {self.state.timestamp} · {self.state.signal_ticker}"
        )

    def _apply_tape_and_news(self) -> None:
        if self.state is None:
            return
        self.ticker_banner.set_tape_items(self.state.ticker_tape)
        self.ticker_banner.set_news_items(self.state.news_items[:5])

    def start_refresh(self) -> None:
        """Reload dashboard state on a background thread."""
        if self._refreshing:
            return
        self._refreshing = True
        if self._refresh_btn is not None:
            self._refresh_btn.setEnabled(False)
            self._refresh_btn.setText("Refreshing…")
        thread = _StateLoaderThread(self)
        thread.loaded.connect(self._on_state_loaded)
        thread.failed.connect(self._on_state_failed)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_loader_finished)
        self._loader_thread = thread
        thread.start()

    def _on_loader_finished(self) -> None:
        self._refreshing = False
        self._loader_thread = None
        if self._refresh_btn is not None:
            self._refresh_btn.setEnabled(True)
            self._refresh_btn.setText("Refresh ↻")

    def _on_state_loaded(self, state: Phase2DashboardState) -> None:
        self.state = state
        self._populate_body()
        self._apply_tape_and_news()
        self._update_status_label()
        self.state_refreshed.emit(state)

    def _on_state_failed(self, message: str) -> None:
        if self._status_label is not None:
            self._status_label.setText(f"Refresh failed: {message[:80]}")

    def refresh_state(self) -> None:
        """Sync reload (blocks UI) — prefer start_refresh()."""
        self.state = load_dashboard_state()
        self._populate_body()
        self._apply_tape_and_news()
        self._update_status_label()
        self.state_refreshed.emit(self.state)

    def _refresh_tape_light(self) -> None:
        if self.state is None:
            return
        symbols = list(dict.fromkeys(TAPE_SYMBOLS + self.state.watchlist))
        self.ticker_banner.set_tape_items(fetch_ticker_tape(symbols))
        news_symbols = list(dict.fromkeys(self.state.watchlist + ["SPY", "AAPL"]))
        self.ticker_banner.set_news_items(fetch_market_news(news_symbols)[:5])

    def _section(self, text: str, badge: str | None = None) -> QLabel:
        lbl = QLabel(f"{text}  {badge or ''}".strip())
        lbl.setStyleSheet("font-size: 10px; font-weight: 600; color: #888; letter-spacing: 1px; margin-top: 8px;")
        return lbl

    def _divider(self) -> QFrame:
        f = QFrame()
        f.setFrameShape(QFrame.Shape.HLine)
        f.setStyleSheet("color: #3a3a6a;")
        return f

    def _consensus_strip(self) -> QFrame:
        f = QFrame()
        f.setStyleSheet("background: #2a2a4a; border: 1px solid #3a3a6a; border-radius: 8px; padding: 8px;")
        lay = QHBoxLayout(f)
        for item in self.state.consensus:
            col = QVBoxLayout()
            col.addWidget(QLabel(item.name))
            bar = QFrame()
            bar.setFixedHeight(4)
            bar.setStyleSheet(f"background: {item.color}; border-radius: 2px;")
            col.addWidget(bar)
            col.addWidget(QLabel(f"{item.score:.2f}"))
            lay.addLayout(col)
        return f

    def _execution_block(self) -> QFrame:
        ex = self.state.execution
        f = QFrame()
        f.setStyleSheet("background: #2a2a4a; border: 1px solid #3a3a6a; border-radius: 8px; padding: 10px;")
        lay = QVBoxLayout(f)
        lay.addWidget(QLabel(f"Smart order routing · VaR-gated — routed to {ex['broker']}"))
        lay.addWidget(QLabel(" → ".join(ex["route_steps"])))
        lay.addWidget(
            QLabel(
                f"VaR: −${abs(ex['post_trade_var']):,.0f} < ${ex['var_cap']:,.0f} ✓  |  "
                f"Size: {ex['raw_qty']} → {ex['sized_qty']}  |  Slippage: {ex['slippage_bps']:.1f} bps"
            )
        )
        return f

    def _agent_grid(self) -> QGridLayout:
        g = QGridLayout()
        for i, ag in enumerate(self.state.agents):
            card = QFrame()
            card.setStyleSheet("background: #1f1f3a; border: 1px solid #3a3a6a; border-radius: 8px; padding: 8px;")
            vl = QVBoxLayout(card)
            vl.addWidget(QLabel(f"{ag['name']} — {ag['signal']} ({ag['score']:.2f})"))
            vl.addWidget(QLabel(ag["strategy"]))
            tag_row = QHBoxLayout()
            for t, active in ag["tickers"]:
                btn = QPushButton(t)
                color = "#00ff88" if active else "#b8b8d0"
                btn.setStyleSheet(
                    f"font-size: 10px; border: 1px solid #3a3a6a; border-radius: 3px; color: {color}; padding: 2px 4px;"
                )
                btn.setFlat(True)
                btn.clicked.connect(lambda _c, sym=t: self._open_chart(sym))
                tag_row.addWidget(btn)
            tag_row.addStretch()
            vl.addLayout(tag_row)
            if ag.get("macro_pill"):
                pill = QLabel(ag["macro_pill"])
                pill.setStyleSheet("color: #00d4ff; font-size: 10px;")
                vl.addWidget(pill)
            g.addWidget(card, i // 2, i % 2)
        return g

    def _workflows(self) -> QVBoxLayout:
        v = QVBoxLayout()
        for wf in self.state.workflows:
            v.addWidget(QLabel(f"{wf.name} [{wf.badge}]"))
        return v

    def _ipo_panel(self) -> QVBoxLayout:
        v = QVBoxLayout()
        for ipo in self.state.ipo_suggestions[:6]:
            card = QFrame()
            card.setStyleSheet(
                "background: #2a2a4a; border: 1px solid #3a3a6a; border-radius: 8px; padding: 8px;"
            )
            lay = QVBoxLayout(card)
            sym = ipo.ticker or "PRE-IPO"
            title = QLabel(f"{ipo.company} · {sym}  [{ipo.status.upper()}]")
            title.setStyleSheet("font-size: 11px; font-weight: 600;")
            lay.addWidget(title)
            lay.addWidget(QLabel(f"{ipo.sector} · {ipo.est_window}"))
            agents = ", ".join(ipo.leading_agents) if ipo.leading_agents else "—"
            lay.addWidget(QLabel(f"Score {ipo.composite_score:.2f} · {ipo.recommendation} · {agents}"))
            note = QLabel(ipo.entry_note)
            note.setWordWrap(True)
            note.setStyleSheet("font-size: 10px; color: #b8b8d0;")
            lay.addWidget(note)
            if ipo.ticker:
                btn = QPushButton("📈 Chart")
                btn.setStyleSheet("font-size: 10px;")
                btn.clicked.connect(lambda _c, t=ipo.ticker: self._open_chart(t))
                lay.addWidget(btn)
            v.addWidget(card)
        if not self.state.ipo_suggestions:
            v.addWidget(QLabel("No IPO candidates meet agent thresholds."))
        return v

    def _risk_panel(self) -> QVBoxLayout:
        r = self.state.risk
        v = QVBoxLayout()
        v.addWidget(QLabel(f"VaR (95%): −${abs(r['var_95']):,}"))
        v.addWidget(QLabel(f"Sharpe: {r['sharpe']:.2f}"))
        v.addWidget(QLabel(f"Max DD: {r['max_dd']:.1f}% / {r['dd_limit']:.0f}% limit"))
        v.addWidget(QLabel(f"Sizing: {r['sizing_model']}"))
        return v

    def _positions(self) -> QVBoxLayout:
        v = QVBoxLayout()
        for pos in self.state.positions:
            row = QHBoxLayout()
            left = QVBoxLayout()
            left.addWidget(QLabel(pos.ticker))
            left.addWidget(QLabel(f"{pos.side} · {pos.quantity}"))
            row.addLayout(left)
            row.addStretch()
            sign = "+" if pos.pnl >= 0 else ""
            color = "#00ff88" if pos.pnl >= 0 else "#ff4757"
            pnl = QLabel(f"{sign}${abs(pos.pnl):,.0f} ({sign}{pos.pnl_pct:.1f}%)")
            pnl.setStyleSheet(f"color: {color}; font-weight: 600;")
            row.addWidget(pnl)
            btn = QPushButton("📈")
            btn.setFixedSize(22, 22)
            btn.clicked.connect(lambda _c, t=pos.ticker: self._open_chart(t))
            row.addWidget(btn)
            wrap = QWidget()
            wrap.setLayout(row)
            v.addWidget(wrap)
        if not self.state.positions:
            v.addWidget(
                QLabel(
                    "No open positions. Connect IBKR (GTP_IBKR_USE_STUB=0) or submit trades via the execution bridge."
                )
            )
        return v

    def _backtest_grid(self) -> QGridLayout:
        bt = self.state.backtest
        g = QGridLayout()
        for i, (k, val) in enumerate(
            [
                ("Sharpe", bt["sharpe"]),
                ("Max DD", f"{bt['max_dd']}%"),
                ("Win rate", f"{bt['win_rate']}%"),
                ("Return", f"{bt['total_return']:+.1f}%"),
            ]
        ):
            g.addWidget(QLabel(f"{k}: {val}"), i // 2, i % 2)
        return g
