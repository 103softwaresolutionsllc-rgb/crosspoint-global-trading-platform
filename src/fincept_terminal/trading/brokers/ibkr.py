"""
Interactive Brokers adapter for Fincept Terminal (wraps global_trading connector).
"""

from __future__ import annotations

from typing import Any

from .base import BaseBroker, BrokerAccount, BrokerPosition


class InteractiveBrokersBroker(BaseBroker):
    """Async broker facade; live orders route through global_trading IBKR connector."""

    def __init__(self) -> None:
        super().__init__(name="interactive_brokers")
        self._credentials: dict[str, str] = {}

    async def connect(self, credentials: dict[str, str]) -> bool:
        self._credentials = credentials
        self.is_connected = True
        self.account_info = BrokerAccount(
            account_id=credentials.get("account_id", "IBKR-PAPER"),
            broker_name="interactive_brokers",
            cash_balance=0.0,
            portfolio_value=0.0,
            buying_power=0.0,
            margin_available=0.0,
            day_trades=0,
            pattern_day_trader=False,
            last_updated=__import__("datetime").datetime.now(),
        )
        return True

    async def disconnect(self) -> None:
        self.is_connected = False

    async def get_account_info(self) -> BrokerAccount:
        if not self.account_info:
            raise RuntimeError("Not connected")
        return self.account_info

    async def get_positions(self) -> list[BrokerPosition]:
        return []

    async def place_order(self, order: Any) -> Any:
        raise NotImplementedError("Use global_trading.connectors.ibkr for order placement")

    async def cancel_order(self, order_id: str) -> bool:
        return False

    async def get_order_status(self, order_id: str) -> Any:
        return None
