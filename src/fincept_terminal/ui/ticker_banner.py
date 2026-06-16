"""
Live ticker banner — scrolling quotes and news headlines for Qt dashboards.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget


@dataclass
class TickerUpdate:
    symbol: str
    price: float
    change_pct: float
    timestamp: datetime | None = None


@dataclass
class NewsHeadline:
    title: str
    source: str = ""
    symbol: str = ""
    timestamp: datetime | None = None


class LiveTickerBanner(QFrame):
    """Horizontally scrolling live tape + optional news strip."""

    def __init__(self, parent: QWidget | None = None, max_items: int = 40):
        super().__init__(parent)
        self._tape: deque[TickerUpdate] = deque(maxlen=max_items)
        self._news: deque[NewsHeadline] = deque(maxlen=20)
        self._offset = 0
        self._build_ui()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick_scroll)
        self._timer.start(50)

    def _build_ui(self) -> None:
        self.setStyleSheet(
            "LiveTickerBanner { background: #1f1f3a; border-bottom: 1px solid #3a3a6a; }"
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        tape_row = QHBoxLayout()
        tape_row.setContentsMargins(0, 0, 0, 0)
        self._live_label = QLabel("LIVE")
        self._live_label.setFixedWidth(52)
        self._live_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._live_label.setStyleSheet(
            "color: #00d4ff; font-size: 10px; font-weight: 700; "
            "border-right: 1px solid #3a3a6a; background: #2a2a4a; padding: 6px;"
        )
        self._tape_label = QLabel("Waiting for market data…")
        self._tape_label.setStyleSheet("color: #b8b8d0; font-size: 11px; padding: 6px 10px;")
        tape_row.addWidget(self._live_label)
        tape_row.addWidget(self._tape_label, 1)
        root.addLayout(tape_row)

        self._news_label = QLabel("")
        self._news_label.setStyleSheet(
            "color: #888; font-size: 10px; padding: 4px 12px; border-top: 1px solid #3a3a6a;"
        )
        self._news_label.setVisible(False)
        root.addWidget(self._news_label)

    def set_tape_items(self, items) -> None:
        """Replace tape contents from TickerTapeItem list."""
        self._tape.clear()
        for item in items:
            self._tape.append(TickerUpdate(item.label, item.price, item.change_pct))
        self._refresh_tape_text()

    def set_news_items(self, items) -> None:
        """Replace news strip from NewsItem list."""
        self._news.clear()
        for item in items:
            self._news.append(NewsHeadline(item.title, item.publisher, item.symbol))
        if self._news:
            self._news_label.setVisible(True)
            self._refresh_news_text()
        else:
            self._news_label.setVisible(False)

    def add_ticker_update(
        self, symbol: str, price: float, change_pct: float, *, timestamp: datetime | None = None
    ) -> None:
        self._tape.append(TickerUpdate(symbol, price, change_pct, timestamp))
        self._refresh_tape_text()

    def add_news_headline(
        self, title: str, source: str = "", symbol: str = "", *, timestamp: datetime | None = None
    ) -> None:
        self._news.append(NewsHeadline(title, source, symbol, timestamp))
        self._news_label.setVisible(True)
        self._refresh_news_text()

    def _refresh_tape_text(self) -> None:
        parts: list[str] = []
        for item in self._tape:
            sign = "+" if item.change_pct >= 0 else ""
            color_tag = "▲" if item.change_pct >= 0 else "▼"
            parts.append(
                f"{item.symbol} ${item.price:,.2f} {color_tag}{sign}{item.change_pct:.2f}%"
            )
        text = "   ·   ".join(parts * 2) if parts else "Waiting for market data…"
        self._tape_label.setText(text)

    def _refresh_news_text(self) -> None:
        if not self._news:
            return
        latest = list(self._news)[-3:]
        parts = [f"[{n.symbol or 'MKT'}] {n.title}" for n in latest]
        self._news_label.setText("  |  ".join(parts))

    def _tick_scroll(self) -> None:
        if not self._tape:
            return
        self._offset = (self._offset + 2) % 10000
        margin = 12 - (self._offset % 24)
        self._tape_label.setContentsMargins(margin, 6, 10, 6)
