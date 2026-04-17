from __future__ import annotations

from global_trading.core.domain import InstrumentId


class MarketDataAgent:
    """Normalizes quotes; v0 uses configurable static marks for simulation."""

    def __init__(self, marks: dict[str, float] | None = None) -> None:
        self._marks = marks or {}

    def mark_price(self, instrument: InstrumentId) -> float | None:
        return self._marks.get(instrument.symbol, 100.0)
