"""Slippage and market impact models for execution simulation."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class SlippageConfig:
    bps: float = 5.0
    sqrt_impact_coeff: float = 0.1


def estimate_slippage(
    price: float,
    *,
    quantity: float = 1.0,
    avg_daily_volume: float = 1_000_000.0,
    config: SlippageConfig | None = None,
) -> float:
    """Estimate slippage in price units (linear bps + sqrt market impact)."""
    cfg = config or SlippageConfig()
    linear = price * (cfg.bps / 10_000)
    participation = quantity / max(avg_daily_volume, 1.0)
    impact = price * cfg.sqrt_impact_coeff * math.sqrt(participation)
    return linear + impact


def apply_slippage(
    price: float,
    *,
    side: str,
    quantity: float = 1.0,
    config: SlippageConfig | None = None,
) -> float:
    """Apply slippage to a fill price (buy pays more, sell receives less)."""
    slip = estimate_slippage(price, quantity=quantity, config=config)
    if side.lower() == "buy":
        return price + slip
    return price - slip
