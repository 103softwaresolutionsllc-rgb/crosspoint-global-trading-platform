"""
Alpaca broker adapter (stub — requires ALPACA_API_KEY).
"""

from __future__ import annotations

import os
from typing import Any

from .base import BaseBroker, BrokerAccount, BrokerPosition


class AlpacaBroker(BaseBroker):
    """Stub Alpaca broker; implement with alpaca-py for production."""

    def __init__(self) -> None:
        super().__init__(name="alpaca")
        self._api_key = os.environ.get("ALPACA_API_KEY", "")

    async def connect(self, credentials: dict[str, str]) -> bool:
        self._api_key = credentials.get("api_key", self._api_key)
        if not self._api_key:
            return False
        self.is_connected = True
        self.account_info = BrokerAccount(
            account_id=credentials.get("account_id", "alpaca-paper"),
            broker_name="alpaca",
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
        raise NotImplementedError("Alpaca live orders not yet implemented")

    async def cancel_order(self, order_id: str) -> bool:
        return False

    async def get_order_status(self, order_id: str) -> Any:
        return None
