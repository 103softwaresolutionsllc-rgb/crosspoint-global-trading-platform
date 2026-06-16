"""Smart Order Routing — select best broker for an order."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Protocol

from global_trading.core.domain import Order, TradeIntent


@dataclass
class BrokerScore:
    broker_id: str
    latency_ms: float = 50.0
    fill_rate: float = 0.95
    fee_bps: float = 1.0

    @property
    def composite_score(self) -> float:
        """Higher is better: fast fills, high fill rate, low fees."""
        latency_penalty = self.latency_ms / 1000.0
        fee_penalty = self.fee_bps / 100.0
        return self.fill_rate - latency_penalty - fee_penalty


class BrokerConnector(Protocol):
    broker_id: str

    def place_order(self, order: Order) -> Order: ...


class SmartOrderRouter:
    """Route orders to the highest-scoring registered broker."""

    def __init__(self) -> None:
        self._brokers: dict[str, BrokerConnector] = {}
        self._scores: dict[str, BrokerScore] = {}

    def register(self, broker: BrokerConnector, score: BrokerScore | None = None) -> None:
        bid = broker.broker_id
        self._brokers[bid] = broker
        self._scores[bid] = score or BrokerScore(broker_id=bid)

    def update_score(self, broker_id: str, **kwargs: float) -> None:
        if broker_id not in self._scores:
            return
        current = self._scores[broker_id]
        self._scores[broker_id] = BrokerScore(
            broker_id=broker_id,
            latency_ms=kwargs.get("latency_ms", current.latency_ms),
            fill_rate=kwargs.get("fill_rate", current.fill_rate),
            fee_bps=kwargs.get("fee_bps", current.fee_bps),
        )

    def select_broker(self) -> str | None:
        if not self._scores:
            return None
        return max(self._scores, key=lambda k: self._scores[k].composite_score)

    def route_intent(self, intent: TradeIntent, order_builder: Callable[[TradeIntent], Order]) -> Order | None:
        broker_id = self.select_broker()
        if broker_id is None:
            return None
        broker = self._brokers[broker_id]
        order = order_builder(intent)
        return broker.place_order(order)
