"""Full-size slide-over chart panel for Qt6 (triggered from positions / agent tickers)."""

from __future__ import annotations

from pathlib import Path

import yfinance as yf
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QComboBox, QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from .charts import SparklineWidget

_PERIOD = {"1 Day": "1d", "5 Days": "5d", "1 Month": "1mo", "3 Months": "3mo"}


class ChartSlideoverDialog(QDialog):
    """Modal slide-over with full-height OHLC/sparkline — no dashboard layout shift."""

    def __init__(self, ticker: str, parent=None):
        super().__init__(parent)
        self.ticker = ticker.replace("/", "-")
        self.setWindowTitle(f"{self.ticker} · Price action")
        self.setModal(True)
        self.setMinimumSize(520, 480)
        self.setStyleSheet("background: #1f1f3a; color: white;")

        layout = QVBoxLayout(self)
        header = QHBoxLayout()
        header.addWidget(QLabel(f"{self.ticker}", styleSheet="font-size: 14px; font-weight: 600; color: #00d4ff;"))
        header.addStretch()
        self._period = QComboBox()
        self._period.addItems(list(_PERIOD.keys()))
        self._period.setCurrentText("1 Month")
        self._period.currentTextChanged.connect(self._reload)
        header.addWidget(self._period)
        close_btn = QPushButton("×")
        close_btn.setFlat(True)
        close_btn.clicked.connect(self.close)
        header.addWidget(close_btn)
        layout.addLayout(header)

        self._chart = SparklineWidget([], positive=True)
        self._chart.setMinimumHeight(360)
        layout.addWidget(self._chart)
        self._reload(self._period.currentText())

    def _reload(self, label: str) -> None:
        period = _PERIOD.get(label, "1mo")
        try:
            hist = yf.Ticker(self.ticker).history(period=period)
            prices = [float(c) for c in hist["Close"].tolist()] if not hist.empty else []
            positive = prices[-1] >= prices[0] if len(prices) > 1 else True
            self._chart.prices = prices or [1.0, 1.0]
            self._chart.positive = positive
            self._chart.update()
        except Exception:
            self._chart.prices = [1.0, 0.9]
            self._chart.positive = False
            self._chart.update()


def brand_logo_path() -> Path:
    return Path(__file__).resolve().parents[3] / "assets" / "android-chrome-192x192.png"
