from __future__ import annotations

from global_trading.core.domain import (
    AssetClass,
    InstrumentId,
    OrderSide,
    OrderType,
    TradeIntent,
    Venue,
)


class SignalAgent:
    """Produces trade intents (strategy layer). Replace with ML/rules per strategy."""

    def __init__(self, strategy_name: str = "demo_momentum") -> None:
        self.strategy_name = strategy_name

    def generate_demo_intent(self) -> TradeIntent:
        iid = InstrumentId(
            symbol="DEMO",
            venue=Venue.BROKER_GENERIC,
            asset_class=AssetClass.EQUITY,
        )
        return TradeIntent(
            instrument=iid,
            side=OrderSide.BUY,
            quantity=1.0,
            order_type=OrderType.MARKET,
            rationale="demo intent",
            strategy_name=self.strategy_name,
        )


class StaticIntentSignal:
    """Fixed intent for tests/CLI (strategy bypass)."""

    def __init__(self, intent: TradeIntent, strategy_name: str = "static") -> None:
        self._intent = intent
        self.strategy_name = strategy_name

    def generate_demo_intent(self) -> TradeIntent:
        return self._intent
