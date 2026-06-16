from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime

from global_trading.core.domain import Money, TradeIntent


@dataclass
class RiskConfig:
    kill_switch: bool = False
    max_daily_loss_base: float = 10_000.0
    base_currency: str = "USD"
    max_notional_per_order: float | None = None
    max_position_qty: dict[str, float] = field(default_factory=dict)
    allowed_prefixes: list[str] | None = None
    max_drawdown_pct: float | None = None
    var_position_fraction: float | None = None

    def __post_init__(self) -> None:
        if self.max_daily_loss_base < 0:
            raise ValueError("max_daily_loss_base must be non-negative")
        if self.max_drawdown_pct is not None and not 0 < self.max_drawdown_pct <= 1:
            raise ValueError("max_drawdown_pct must be between 0 and 1")


@dataclass
class RiskState:
    """Tracks daily PnL and portfolio drawdown for guardrails."""

    day: date
    realized_pnl_base: float = 0.0
    peak_equity: float = 0.0
    current_equity: float = 0.0


@dataclass
class RiskDecision:
    allowed: bool
    reason: str
    capped_quantity: float | None = None


class RiskEngine:
    def __init__(self, config: RiskConfig, state: RiskState | None = None) -> None:
        self.config = config
        today = datetime.now(UTC).date()
        self.state = state or RiskState(day=today)

    def _rollover_if_needed(self) -> None:
        today = datetime.now(UTC).date()
        if today != self.state.day:
            self.state = RiskState(day=today, realized_pnl_base=0.0)

    def record_pnl(self, delta_base: float) -> None:
        self._rollover_if_needed()
        self.state.realized_pnl_base += delta_base

    def update_equity(self, equity: float) -> None:
        """Update peak equity and current equity for drawdown checks."""
        self._rollover_if_needed()
        self.state.current_equity = equity
        if equity > self.state.peak_equity:
            self.state.peak_equity = equity

    def current_drawdown_pct(self) -> float:
        if self.state.peak_equity <= 0:
            return 0.0
        return (self.state.peak_equity - self.state.current_equity) / self.state.peak_equity

    def evaluate_intent(
        self,
        intent: TradeIntent,
        *,
        mark_price: float | None,
        fx_to_base: float = 1.0,
    ) -> RiskDecision:
        self._rollover_if_needed()
        if self.config.kill_switch:
            return RiskDecision(allowed=False, reason="kill_switch_active")

        if self.state.realized_pnl_base <= -abs(self.config.max_daily_loss_base):
            return RiskDecision(allowed=False, reason="max_daily_loss_breached")

        if self.config.max_drawdown_pct is not None:
            dd = self.current_drawdown_pct()
            if dd >= self.config.max_drawdown_pct:
                return RiskDecision(allowed=False, reason="max_drawdown_breached")

        sym = intent.instrument.symbol
        if self.config.allowed_prefixes:
            if not any(sym.startswith(p) for p in self.config.allowed_prefixes):
                return RiskDecision(allowed=False, reason="symbol_not_allowed")

        max_q = self.config.max_position_qty.get(sym)
        qty = intent.quantity
        if max_q is not None and qty > max_q:
            return RiskDecision(allowed=True, reason="capped_to_max_position", capped_quantity=max_q)

        if mark_price is not None and self.config.max_notional_per_order is not None:
            notional = qty * mark_price * fx_to_base
            if notional > self.config.max_notional_per_order:
                cap = self.config.max_notional_per_order / (mark_price * fx_to_base)
                return RiskDecision(allowed=True, reason="capped_to_max_notional", capped_quantity=cap)

        return RiskDecision(allowed=True, reason="ok")

    def validate_order_notional(self, notional: Money, base_equivalent: Money) -> RiskDecision:
        if self.config.kill_switch:
            return RiskDecision(allowed=False, reason="kill_switch_active")
        if self.config.max_notional_per_order and base_equivalent.amount > self.config.max_notional_per_order:
            return RiskDecision(allowed=False, reason="order_notional_exceeds_limit")
        return RiskDecision(allowed=True, reason="ok")
