from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from global_trading.core.domain import Order, OrderSide, OrderStatus, Position


class PositionLedger:
    """Local view of positions from simulated/known fills (for reconciliation)."""

    def __init__(self, account_id: str) -> None:
        self.account_id = account_id
        self._positions: dict[str, Position] = {}

    def _key(self, order: Order) -> str:
        i = order.instrument
        return f"{i.symbol}|{i.venue.value}|{i.asset_class.value}"

    def apply_filled_order(self, order: Order, *, fill_price: float | None = None) -> None:
        if order.status != OrderStatus.FILLED:
            return
        key = self._key(order)
        sign = 1.0 if order.side == OrderSide.BUY else -1.0
        delta = sign * order.quantity
        price = float(fill_price or order.limit_price or 0.0)
        pos = self._positions.get(key)
        if pos is None:
            self._positions[key] = Position(
                account_id=self.account_id,
                venue=order.instrument.venue,
                instrument=order.instrument,
                quantity=delta,
                avg_price=price or None,
                as_of=datetime.now(UTC),
            )
        else:
            new_qty = pos.quantity + delta
            self._positions[key] = replace(
                pos,
                quantity=new_qty,
                avg_price=price or pos.avg_price,
                as_of=datetime.now(UTC),
            )

    def positions(self) -> list[Position]:
        return list(self._positions.values())
