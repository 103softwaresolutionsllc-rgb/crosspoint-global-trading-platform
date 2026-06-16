"""Historical data loader for backtesting."""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import yfinance as yf


def load_ohlcv(
    ticker: str,
    start: str | datetime,
    end: str | datetime,
    *,
    interval: str = "1d",
) -> pd.DataFrame:
    """Load OHLCV bars from Yahoo Finance."""
    data = yf.download(ticker, start=start, end=end, interval=interval, progress=False)
    if data.empty:
        raise ValueError(f"No data returned for {ticker} between {start} and {end}")

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    required = {"Open", "High", "Low", "Close", "Volume"}
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"Missing columns {missing} for {ticker}")

    return data.dropna()
