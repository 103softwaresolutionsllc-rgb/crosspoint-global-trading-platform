from __future__ import annotations

from dataclasses import dataclass

from global_trading.core.domain import TradeIntent


@dataclass
class SizingConfig:
    """Risk-based position sizing parameters."""

    portfolio_value: float = 100_000.0
    var_fraction: float = 0.02
    var_per_share: float | None = None
    max_position_pct: float = 0.10


class PortfolioAgent:
    """Target weights, rebalancing, and VaR-based position sizing."""

    def __init__(self, sizing: SizingConfig | None = None) -> None:
        self.sizing = sizing

    def adjust_intent(self, intent: TradeIntent, *, mark_price: float | None = None) -> TradeIntent:
        if self.sizing is None or mark_price is None or mark_price <= 0:
            return intent

        cfg = self.sizing
        risk_budget = cfg.portfolio_value * cfg.var_fraction

        if cfg.var_per_share and cfg.var_per_share > 0:
            sized_qty = risk_budget / cfg.var_per_share
        else:
            max_notional = cfg.portfolio_value * cfg.max_position_pct
            sized_qty = max_notional / mark_price

        qty = min(intent.quantity, sized_qty)
        if qty <= 0:
            return intent

        from dataclasses import replace

        return replace(intent, quantity=qty, rationale=f"{intent.rationale} [sized]")
