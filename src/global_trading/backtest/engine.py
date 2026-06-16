"""
Historical simulation engine — replays bars through a strategy and tracks PnL.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable

import numpy as np
import pandas as pd

from global_trading.backtest.data import load_ohlcv
from global_trading.execution.slippage import SlippageConfig, apply_slippage


@dataclass
class BacktestConfig:
    ticker: str
    start: str | datetime
    end: str | datetime
    initial_capital: float = 100_000.0
    position_fraction: float = 1.0
    slippage_bps: float = 5.0
    commission_per_trade: float = 1.0


@dataclass
class BacktestResult:
    ticker: str
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    num_trades: int
    final_equity: float
    equity_curve: pd.Series = field(repr=False)
    trades: list[dict] = field(default_factory=list)


def _buy_and_hold_signals(data: pd.DataFrame) -> pd.Series:
    signals = pd.Series(0, index=data.index)
    signals.iloc[0] = 1
    return signals


def _max_drawdown(equity: pd.Series) -> float:
    peak = equity.cummax()
    dd = (equity - peak) / peak
    return float(dd.min())


def _sharpe(returns: pd.Series, periods_per_year: int = 252) -> float:
    if returns.std() == 0:
        return 0.0
    return float(returns.mean() / returns.std() * np.sqrt(periods_per_year))


class BacktestEngine:
    """Bar-by-bar backtester with slippage and commission modeling."""

    STRATEGIES: dict[str, Callable[[pd.DataFrame], pd.Series]] = {
        "buy_hold": _buy_and_hold_signals,
    }

    def __init__(self, config: BacktestConfig) -> None:
        self.config = config
        self.slippage = SlippageConfig(bps=config.slippage_bps)

    def run(
        self,
        strategy: str | Callable[[pd.DataFrame], pd.Series] = "buy_hold",
        data: pd.DataFrame | None = None,
    ) -> BacktestResult:
        bars = data if data is not None else load_ohlcv(
            self.config.ticker, self.config.start, self.config.end
        )

        if isinstance(strategy, str):
            signal_fn = self.STRATEGIES.get(strategy)
            if signal_fn is None:
                raise ValueError(f"Unknown strategy: {strategy}")
        else:
            signal_fn = strategy

        signals = signal_fn(bars)
        cash = self.config.initial_capital
        shares = 0.0
        trades: list[dict] = []
        equity_values: list[float] = []
        wins = 0

        for i, (ts, row) in enumerate(bars.iterrows()):
            price = float(row["Close"])
            signal = int(signals.iloc[i]) if i < len(signals) else 0

            if signal == 1 and shares == 0:
                alloc = cash * self.config.position_fraction
                fill_price = apply_slippage(price, side="buy", config=self.slippage)
                qty = int(alloc / fill_price)
                if qty > 0:
                    cost = qty * fill_price + self.config.commission_per_trade
                    if cost <= cash:
                        cash -= cost
                        shares = qty
                        trades.append(
                            {"date": str(ts), "side": "buy", "qty": qty, "price": fill_price}
                        )

            elif signal == -1 and shares > 0:
                fill_price = apply_slippage(price, side="sell", config=self.slippage)
                proceeds = shares * fill_price - self.config.commission_per_trade
                entry = trades[-1]["price"] if trades else fill_price
                if proceeds > shares * entry:
                    wins += 1
                cash += proceeds
                trades.append(
                    {"date": str(ts), "side": "sell", "qty": shares, "price": fill_price}
                )
                shares = 0.0

            equity_values.append(cash + shares * price)

        equity = pd.Series(equity_values, index=bars.index)
        returns = equity.pct_change().dropna()
        final = float(equity.iloc[-1])
        total_ret = (final - self.config.initial_capital) / self.config.initial_capital

        sell_trades = [t for t in trades if t["side"] == "sell"]
        win_rate = wins / len(sell_trades) if sell_trades else 0.0

        return BacktestResult(
            ticker=self.config.ticker,
            total_return=total_ret,
            sharpe_ratio=_sharpe(returns),
            max_drawdown=_max_drawdown(equity),
            win_rate=win_rate,
            num_trades=len(trades),
            final_equity=final,
            equity_curve=equity,
            trades=trades,
        )
