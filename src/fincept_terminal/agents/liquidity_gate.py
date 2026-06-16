"""
Toxic-flow / HFT liquidity micro-agent.

Monitors order-book imbalance and spread volatility on the live WebSocket stream.
Can pause execution when microstructure conditions are hostile to fundamental entries.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Deque

@dataclass
class LiquiditySnapshot:
    symbol: str
    obi: float
    spread_bps: float
    bid_depth: float
    ask_depth: float
    toxic: bool
    reason: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class LiquidityGateConfig:
    obi_toxic_threshold: float = 0.65
    spread_spike_bps: float = 25.0
    min_depth: float = 100.0
    spread_vol_window: int = 20


class LiquidityGateAgent:
    """Millisecond-scale microstructure gate for execution pause/resume."""

    def __init__(self, config: LiquidityGateConfig | None = None) -> None:
        self.config = config or LiquidityGateConfig()
        self._spread_history: dict[str, Deque[float]] = {}
        self._last_snapshot: dict[str, LiquiditySnapshot] = {}
        self._paused: dict[str, bool] = {}

    def on_order_book(self, book) -> LiquiditySnapshot:
        bids = book.bids or []
        asks = book.asks or []
        bid_depth = sum(level[1] for level in bids[:5]) if bids else 0.0
        ask_depth = sum(level[1] for level in asks[:5]) if asks else 0.0
        total = bid_depth + ask_depth

        best_bid = bids[0][0] if bids else 0.0
        best_ask = asks[0][0] if asks else 0.0
        mid = (best_bid + best_ask) / 2 if best_bid and best_ask else 0.0
        spread_bps = ((best_ask - best_bid) / mid * 10_000) if mid > 0 else 0.0

        obi = (bid_depth - ask_depth) / total if total > 0 else 0.0

        hist = self._spread_history.setdefault(book.symbol, deque(maxlen=self.config.spread_vol_window))
        hist.append(spread_bps)
        spread_vol = 0.0
        if len(hist) >= 5:
            vals = list(hist)
            mean = sum(vals) / len(vals)
            spread_vol = (sum((v - mean) ** 2 for v in vals) / len(vals)) ** 0.5

        toxic = False
        reasons: list[str] = []
        if abs(obi) >= self.config.obi_toxic_threshold:
            toxic = True
            side = "sell" if obi < 0 else "buy"
            reasons.append(f"OBI {obi:.2f} — one-sided {side} pressure")
        if spread_bps >= self.config.spread_spike_bps:
            toxic = True
            reasons.append(f"spread {spread_bps:.1f} bps exceeds cap")
        if spread_vol > self.config.spread_spike_bps * 0.5 and spread_bps > 10:
            toxic = True
            reasons.append(f"spread volatility {spread_vol:.1f} bps")
        if bid_depth < self.config.min_depth or ask_depth < self.config.min_depth:
            toxic = True
            reasons.append("depth evaporating on one or both sides")

        snap = LiquiditySnapshot(
            symbol=book.symbol,
            obi=obi,
            spread_bps=spread_bps,
            bid_depth=bid_depth,
            ask_depth=ask_depth,
            toxic=toxic,
            reason="; ".join(reasons),
            timestamp=book.timestamp,
        )
        self._last_snapshot[book.symbol] = snap
        self._paused[book.symbol] = toxic
        return snap

    def on_quote_spread(self, symbol: str, bid: float, ask: float) -> LiquiditySnapshot:
        """Fallback when full book unavailable — synthesize minimal book."""
        from fincept_terminal.trading.websocket import OrderBookData

        book = OrderBookData(
            symbol=symbol,
            timestamp=datetime.now(UTC),
            bids=[[bid, 1.0]] if bid else [],
            asks=[[ask, 1.0]] if ask else [],
        )
        return self.on_order_book(book)

    def execution_allowed(self, symbol: str) -> bool:
        return not self._paused.get(symbol, False)

    def pause_reason(self, symbol: str) -> str:
        snap = self._last_snapshot.get(symbol)
        return snap.reason if snap and snap.toxic else ""

    def get_snapshot(self, symbol: str) -> LiquiditySnapshot | None:
        return self._last_snapshot.get(symbol)
