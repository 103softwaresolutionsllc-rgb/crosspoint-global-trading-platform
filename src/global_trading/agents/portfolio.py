from __future__ import annotations

from global_trading.core.domain import TradeIntent


class PortfolioAgent:
    """Target weights and rebalancing; v0 passes through."""

    def adjust_intent(self, intent: TradeIntent) -> TradeIntent:
        return intent
