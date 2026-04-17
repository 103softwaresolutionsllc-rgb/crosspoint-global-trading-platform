from __future__ import annotations

from global_trading.core.domain import TradeIntent
from global_trading.core.risk import RiskDecision, RiskEngine


class RiskAgent:
    """Agent wrapper around RiskEngine for orchestration symmetry."""

    def __init__(self, engine: RiskEngine) -> None:
        self.engine = engine

    def check(self, intent: TradeIntent, *, mark_price: float | None, fx_to_base: float = 1.0) -> RiskDecision:
        return self.engine.evaluate_intent(intent, mark_price=mark_price, fx_to_base=fx_to_base)
