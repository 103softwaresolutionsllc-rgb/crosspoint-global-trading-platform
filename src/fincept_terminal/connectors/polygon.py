"""
Polygon.io data connector (stub — requires POLYGON_API_KEY).
"""

from __future__ import annotations

import os
from typing import Any

import pandas as pd


class PolygonConnector:
    """Minimal Polygon connector; extend with polygon-api-client for production use."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.environ.get("POLYGON_API_KEY", "YOUR_POLYGON_API_KEY")

    async def get_data(self, symbol: str, **kwargs: Any) -> pd.DataFrame:
        if self.api_key == "YOUR_POLYGON_API_KEY":
            raise ValueError(
                "Set POLYGON_API_KEY env var or pass api_key to use Polygon connector"
            )
        raise NotImplementedError(
            "Polygon live fetch not yet implemented — install polygon-api-client and extend this module"
        )
