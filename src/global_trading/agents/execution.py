from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from global_trading.core.domain import (
    Order,
    OrderStatus,
    TradeIntent,
    Venue,
)


class ExecutionAgent:
    """Maps approved intents to venue orders with idempotent client_order_id."""

    def intent_to_order(self, intent: TradeIntent, *, account_id: str, venue: Venue) -> Order:
        inst = replace(intent.instrument, venue=venue)
        return Order(
            client_order_id=str(intent.intent_id),
            venue=venue,
            account_id=account_id,
            instrument=inst,
            side=intent.side,
            order_type=intent.order_type,
            quantity=intent.quantity,
            limit_price=intent.limit_price,
            status=OrderStatus.PENDING,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            meta={"strategy": intent.strategy_name},
        )
