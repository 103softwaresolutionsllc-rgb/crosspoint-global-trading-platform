from datetime import UTC, date, datetime

from global_trading.core.domain import AssetClass, InstrumentId, OrderSide, TradeIntent, Venue
from global_trading.core.risk import RiskConfig, RiskEngine, RiskState


def test_drawdown_blocks_orders() -> None:
    engine = RiskEngine(
        RiskConfig(max_drawdown_pct=0.10),
        state=RiskState(day=datetime.now(UTC).date(), peak_equity=100_000, current_equity=85_000),
    )
    intent = TradeIntent(
        instrument=InstrumentId("AAPL", Venue.BROKER_GENERIC, AssetClass.EQUITY),
        side=OrderSide.BUY,
        quantity=10,
    )
    decision = engine.evaluate_intent(intent, mark_price=150.0)
    assert not decision.allowed
    assert decision.reason == "max_drawdown_breached"
