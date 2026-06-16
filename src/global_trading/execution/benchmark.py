"""Execution benchmarking — compare fill price vs arrival price."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ExecutionBenchmark:
    arrival_price: float
    fill_price: float
    quantity: float
    side: str

    @property
    def slippage_bps(self) -> float:
        if self.arrival_price == 0:
            return 0.0
        diff = self.fill_price - self.arrival_price
        if self.side.lower() == "sell":
            diff = -diff
        return (diff / self.arrival_price) * 10_000

    @property
    def implementation_shortfall(self) -> float:
        """Dollar cost of slippage vs arrival."""
        diff = self.fill_price - self.arrival_price
        if self.side.lower() == "sell":
            diff = -diff
        return diff * self.quantity
