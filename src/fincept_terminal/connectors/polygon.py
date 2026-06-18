"""
Polygon.io data connector (stub — requires POLYGON_API_KEY).
"""

from __future__ import annotations

import os
from typing import Any

import pandas as pd


class PolygonConnector:
    """
    Minimal Polygon connector; extend with polygon-api-client for production use.
    
    To implement live fetching:
    1. Install the official Polygon client: `pip install polygon-api-client`
    2. Set `POLYGON_API_KEY` in your `.env` file.
    3. Initialize the REST client inside `__init__`:
       ```python
       from polygon import RESTClient
       self.client = RESTClient(api_key=self.api_key)
       ```
    4. Implement `get_data` using client methods:
       ```python
       # Fetch daily aggregates or trades/quotes
       aggs = self.client.get_aggs(ticker=symbol, multiplier=1, timespan="day", from_="2026-01-01", to="2026-06-01")
       # Parse aggregates to pd.DataFrame
       ```
    """

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.environ.get("POLYGON_API_KEY", "YOUR_POLYGON_API_KEY")

    async def get_data(self, symbol: str, **kwargs: Any) -> pd.DataFrame:
        if self.api_key == "YOUR_POLYGON_API_KEY":
            raise ValueError(
                "Set POLYGON_API_KEY env var or pass api_key to use Polygon connector"
            )
        raise NotImplementedError(
            "Polygon live fetch is not yet implemented. "
            "To resolve this, please install `polygon-api-client` and extend "
            "the `get_data` method using the implementation guidelines documented "
            "in this class docstring."
        )
