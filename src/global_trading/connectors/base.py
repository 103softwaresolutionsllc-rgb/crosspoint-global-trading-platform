from __future__ import annotations

from typing import Protocol

from global_trading.core.domain import Money, Order, Position


class BrokerConnector(Protocol):
    """Venue adapter: normalize broker/exchange behind one interface."""

    venue_name: str
    account_id: str

    def place_order(self, order: Order) -> Order:
        ...

    def cancel_order(self, client_order_id: str) -> bool:
        ...

    def get_positions(self) -> list[Position]:
        ...

    def get_balances(self) -> dict[str, Money]:
        ...
