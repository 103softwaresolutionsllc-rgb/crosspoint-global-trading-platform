from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from global_trading.core.domain import (
    InstrumentId,
    Money,
    Order,
    OrderSide,
    OrderStatus,
    Position,
    Venue,
)
from global_trading.observability.metrics import Metrics


class FakeConnector:
    """In-memory connector for tests and dry runs."""

    def __init__(self, account_id: str = "fake-1", metrics: Metrics | None = None) -> None:
        self.venue_name = "fake"
        self.account_id = account_id
        self._orders: dict[str, Order] = {}
        self._positions: dict[str, Position] = {}
        self._metrics = metrics

    def place_order(self, order: Order) -> Order:
        if order.client_order_id in self._orders:
            return self._orders[order.client_order_id]
        now = datetime.now(UTC)
        filled = replace(
            order,
            status=OrderStatus.FILLED,
            broker_order_id=f"BRK-{order.client_order_id[:8]}",
            updated_at=now,
        )
        self._orders[order.client_order_id] = filled
        self._apply_fill(filled)
        if self._metrics:
            self._metrics.inc("orders_submitted")
            self._metrics.inc("orders_filled")
        return filled

    def cancel_order(self, client_order_id: str) -> bool:
        o = self._orders.get(client_order_id)
        if not o:
            return False
        now = datetime.now(UTC)
        self._orders[client_order_id] = replace(o, status=OrderStatus.CANCELLED, updated_at=now)
        if self._metrics:
            self._metrics.inc("orders_cancelled")
        return True

    def get_positions(self) -> list[Position]:
        return list(self._positions.values())

    def get_balances(self) -> dict[str, Money]:
        return {"USD": Money(amount=1_000_000.0, currency="USD")}

    def _position_key(self, instrument: InstrumentId) -> str:
        return f"{instrument.symbol}|{instrument.venue.value}"

    def _apply_fill(self, order: Order) -> None:
        key = self._position_key(order.instrument)
        sign = 1.0 if order.side == OrderSide.BUY else -1.0
        delta = sign * order.quantity
        mark = float(order.limit_price or 100.0)
        pos = self._positions.get(key)
        if pos is None:
            self._positions[key] = Position(
                account_id=self.account_id,
                venue=order.instrument.venue,
                instrument=order.instrument,
                quantity=delta,
                avg_price=mark,
            )
        else:
            new_qty = pos.quantity + delta
            self._positions[key] = replace(
                pos,
                quantity=new_qty,
                avg_price=mark,
                as_of=datetime.now(UTC),
            )
