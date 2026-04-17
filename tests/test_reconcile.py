from global_trading.core.domain import (
    AssetClass,
    InstrumentId,
    Position,
    Venue,
)
from global_trading.connectors.reconcile import reconcile_positions


def test_reconcile_match() -> None:
    iid = InstrumentId(symbol="A", venue=Venue.BROKER_GENERIC, asset_class=AssetClass.EQUITY)
    p = Position(
        account_id="a1",
        venue=Venue.BROKER_GENERIC,
        instrument=iid,
        quantity=10.0,
    )
    rep = reconcile_positions(account_id="a1", venue=Venue.BROKER_GENERIC, local=[p], remote=[p])
    assert rep.ok


def test_reconcile_mismatch() -> None:
    iid = InstrumentId(symbol="A", venue=Venue.BROKER_GENERIC, asset_class=AssetClass.EQUITY)
    local = [
        Position(
            account_id="a1",
            venue=Venue.BROKER_GENERIC,
            instrument=iid,
            quantity=10.0,
        )
    ]
    remote = [
        Position(
            account_id="a1",
            venue=Venue.BROKER_GENERIC,
            instrument=iid,
            quantity=9.0,
        )
    ]
    rep = reconcile_positions(account_id="a1", venue=Venue.BROKER_GENERIC, local=local, remote=remote)
    assert not rep.ok
    assert len(rep.mismatches) == 1
