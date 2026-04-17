from global_trading.core.domain import (
    AssetClass,
    InstrumentId,
    OrderSide,
    TradeIntent,
    Venue,
)
from global_trading.core.risk import RiskConfig, RiskEngine


def test_kill_switch_blocks() -> None:
    eng = RiskEngine(RiskConfig(kill_switch=True))
    intent = TradeIntent(
        instrument=InstrumentId(symbol="X", venue=Venue.BROKER_GENERIC, asset_class=AssetClass.EQUITY),
        side=OrderSide.BUY,
        quantity=1.0,
    )
    d = eng.evaluate_intent(intent, mark_price=10.0)
    assert not d.allowed
    assert d.reason == "kill_switch_active"


def test_notional_cap() -> None:
    eng = RiskEngine(RiskConfig(kill_switch=False, max_notional_per_order=1000.0))
    intent = TradeIntent(
        instrument=InstrumentId(symbol="X", venue=Venue.BROKER_GENERIC, asset_class=AssetClass.EQUITY),
        side=OrderSide.BUY,
        quantity=100.0,
    )
    d = eng.evaluate_intent(intent, mark_price=20.0)
    assert d.allowed
    assert d.capped_quantity is not None
    assert abs(d.capped_quantity - 50.0) < 1e-6
