"""
FRED macro context pipeline — fetch, cache, regime detection, and per-agent adjustments.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field, replace
from typing import Any

import pandas as pd

from fincept_terminal.agents.base import AgentResult

MACRO_SERIES = {
    "gdp": "GDPC1",
    "cpi": "CPIAUCSL",
    "unemployment": "UNRATE",
    "fed_funds": "FEDFUNDS",
    "yield_10y": "DGS10",
    "yield_2y": "DGS2",
}

FRED_API_KEY_ENV = "FRED_API_KEY"
CACHE_TTL_SECONDS = 3600


@dataclass
class MacroSnapshot:
    gdp_growth_yoy: float
    cpi_yoy: float
    unemployment: float
    fed_funds_rate: float
    yield_curve_10y2y: float
    regime: str
    as_of: str
    source: str = "fred"
    series_raw: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "gdp_growth_yoy": self.gdp_growth_yoy,
            "cpi_yoy": self.cpi_yoy,
            "unemployment": self.unemployment,
            "fed_funds_rate": self.fed_funds_rate,
            "yield_curve_10y2y": self.yield_curve_10y2y,
            "regime": self.regime,
            "as_of": self.as_of,
            "source": self.source,
        }

    def pill_text(self) -> str:
        gdp_sign = "+" if self.gdp_growth_yoy >= 0 else ""
        cpi_note = "cooling" if self.cpi_yoy < 3.0 else "elevated"
        return f"GDP {gdp_sign}{self.gdp_growth_yoy:.1f}% · CPI {cpi_note}"


_cache: MacroSnapshot | None = None
_cache_at: float = 0.0


def _yoy_from_series(df: pd.DataFrame, periods: int = 12) -> float | None:
    if df is None or df.empty or len(df) <= periods:
        return None
    latest = float(df["value"].iloc[-1])
    prior = float(df["value"].iloc[-1 - periods])
    if prior == 0:
        return None
    return ((latest / prior) - 1) * 100


def _qoq_annualized_gdp(df: pd.DataFrame) -> float | None:
    """Quarterly GDP YoY % from GDPC1."""
    if df is None or df.empty or len(df) <= 4:
        return None
    latest = float(df["value"].iloc[-1])
    prior = float(df["value"].iloc[-5])
    if prior == 0:
        return None
    return ((latest / prior) - 1) * 100


def _latest(df: pd.DataFrame) -> float | None:
    if df is None or df.empty:
        return None
    return float(df["value"].iloc[-1])


def detect_regime(
    *,
    gdp_growth: float,
    cpi_yoy: float,
    unemployment: float,
    yield_curve: float,
) -> str:
    if yield_curve < -0.1 and unemployment > 5.0:
        return "recession_risk"
    if yield_curve < 0:
        return "late_cycle"
    if gdp_growth > 2.5 and cpi_yoy < 3.0:
        return "expansion"
    if cpi_yoy > 4.0:
        return "inflationary"
    return "mid_cycle"


def _fallback_snapshot() -> MacroSnapshot:
    """Demo macro data when FRED_API_KEY is unavailable."""
    return MacroSnapshot(
        gdp_growth_yoy=2.1,
        cpi_yoy=3.2,
        unemployment=4.1,
        fed_funds_rate=5.33,
        yield_curve_10y2y=-0.15,
        regime="late_cycle",
        as_of="unavailable",
        source="fallback",
    )


async def fetch_macro_snapshot(api_key: str | None = None) -> MacroSnapshot:
    """Fetch key FRED series and build normalized macro snapshot."""
    key = api_key if api_key is not None else os.environ.get(FRED_API_KEY_ENV, "")
    if not key or key == "YOUR_FRED_API_KEY":
        return _fallback_snapshot()

    from fincept_terminal.connectors.fred import FREDConnector

    async with FREDConnector(api_key=key) as conn:
        series = await conn.get_multiple_series(list(MACRO_SERIES.values()))

    gdp_df = series.get(MACRO_SERIES["gdp"])
    cpi_df = series.get(MACRO_SERIES["cpi"])

    gdp_growth = _qoq_annualized_gdp(gdp_df) or 0.0
    cpi_yoy = _yoy_from_series(cpi_df, periods=12) or 0.0
    unemployment = _latest(series.get(MACRO_SERIES["unemployment"])) or 0.0
    fed_funds = _latest(series.get(MACRO_SERIES["fed_funds"])) or 0.0
    y10 = _latest(series.get(MACRO_SERIES["yield_10y"])) or 0.0
    y2 = _latest(series.get(MACRO_SERIES["yield_2y"])) or 0.0
    yield_curve = y10 - y2

    as_of = ""
    if gdp_df is not None and not gdp_df.empty:
        as_of = str(gdp_df.index[-1].date())

    regime = detect_regime(
        gdp_growth=gdp_growth,
        cpi_yoy=cpi_yoy,
        unemployment=unemployment,
        yield_curve=yield_curve,
    )

    return MacroSnapshot(
        gdp_growth_yoy=round(gdp_growth, 2),
        cpi_yoy=round(cpi_yoy, 2),
        unemployment=round(unemployment, 2),
        fed_funds_rate=round(fed_funds, 2),
        yield_curve_10y2y=round(yield_curve, 2),
        regime=regime,
        as_of=as_of,
        source="fred",
        series_raw={
            "GDPC1": gdp_growth,
            "CPIAUCSL": cpi_yoy,
            "UNRATE": unemployment,
            "FEDFUNDS": fed_funds,
            "T10Y2Y": yield_curve,
        },
    )


async def get_macro_context(*, force_refresh: bool = False) -> MacroSnapshot:
    """Return cached macro snapshot, refreshing if stale."""
    global _cache, _cache_at
    now = time.time()
    if not force_refresh and _cache is not None and (now - _cache_at) < CACHE_TTL_SECONDS:
        return _cache
    _cache = await fetch_macro_snapshot()
    _cache_at = now
    return _cache


def invalidate_macro_cache() -> None:
    global _cache, _cache_at
    _cache = None
    _cache_at = 0.0


async def resolve_macro(kwargs: dict[str, Any]) -> MacroSnapshot:
    """Resolve macro from kwargs or shared cache."""
    if "macro" in kwargs and kwargs["macro"] is not None:
        raw = kwargs["macro"]
        if isinstance(raw, MacroSnapshot):
            return raw
        if isinstance(raw, dict):
            return MacroSnapshot(
                gdp_growth_yoy=raw.get("gdp_growth_yoy", 0),
                cpi_yoy=raw.get("cpi_yoy", 0),
                unemployment=raw.get("unemployment", 0),
                fed_funds_rate=raw.get("fed_funds_rate", 0),
                yield_curve_10y2y=raw.get("yield_curve_10y2y", 0),
                regime=raw.get("regime", "mid_cycle"),
                as_of=raw.get("as_of", ""),
                source=raw.get("source", "injected"),
            )
    add = kwargs.get("additional_data") or {}
    if isinstance(add, dict) and "macro" in add:
        return await resolve_macro({"macro": add["macro"]})
    return await get_macro_context()


def _adjust_confidence(agent_key: str, confidence: float, macro: MacroSnapshot) -> tuple[float, list[str], list[str], list[str]]:
    """Per-agent macro adjustments. Returns (confidence, notes, risks, catalysts)."""
    notes: list[str] = []
    risks: list[str] = []
    catalysts: list[str] = []
    c = confidence

    if agent_key == "buffett":
        if macro.yield_curve_10y2y < 0:
            c *= 0.92
            notes.append("Inverted yield curve — tighter margin of safety applied")
            risks.append("Late-cycle macro: inverted yield curve")
        if macro.regime in ("late_cycle", "recession_risk"):
            c *= 0.95
            notes.append(f"Regime '{macro.regime}' — defensive posture")
        if macro.regime == "expansion" and macro.cpi_yoy < 3.0:
            c = min(1.0, c * 1.03)
            catalysts.append("Stable expansion supports quality compounders")

    elif agent_key == "graham":
        if macro.unemployment > 4.5:
            c = min(1.0, c + 0.05)
            notes.append("Rising unemployment favors deep-value net-nets")
            catalysts.append("Labor softening may widen value spreads")
        if macro.cpi_yoy > 4.0:
            c = min(1.0, c + 0.03)
            notes.append("Elevated CPI — defensive value bias")
        if macro.yield_curve_10y2y < 0:
            risks.append("Macro headwind: yield curve inversion")

    elif agent_key == "lynch":
        fed_target = 2.5
        if macro.cpi_yoy > fed_target + 1.0:
            c *= 0.88
            notes.append(f"CPI {macro.cpi_yoy:.1f}% above target — GARP scores reduced")
            risks.append("Inflation compresses growth multiples")
        if macro.gdp_growth_yoy > 2.5:
            c = min(1.0, c + 0.05)
            catalysts.append(f"GDP growth {macro.gdp_growth_yoy:.1f}% supports earnings")

    elif agent_key == "dunlap":
        if macro.gdp_growth_yoy > 2.5:
            c = min(1.0, c + 0.06)
            notes.append("Strong GDP favors elite compounders")
            catalysts.append("Secular growth tailwind from expansion")
        if macro.regime == "recession_risk":
            c *= 0.85
            notes.append("Recession risk — quality bar raised")
            risks.append("Macro slowdown threatens compounder multiples")

    elif agent_key == "dalio":
        if macro.fed_funds_rate > 4.5:
            c *= 0.90
            notes.append("High Fed Funds rate — multiple compression drag applied")
            risks.append("Tight monetary policy increases cost of capital")
        if macro.yield_curve_10y2y < 0:
            c *= 0.95
            notes.append("Inverted yield curve — elevated credit contraction risk")
            risks.append("Yield curve inversion suggests credit contraction risk")
        if macro.regime == "inflationary":
            notes.append("Inflationary regime — bias towards pricing power and commodity linkages")
        elif macro.regime == "recession_risk":
            c *= 0.88
            notes.append("Recession risk — defensive posture with capital preservation focus")

    return max(0.0, min(1.0, c)), notes, risks, catalysts


def apply_macro_to_result(result: AgentResult, macro: MacroSnapshot, agent_key: str) -> AgentResult:
    """Apply macro adjustments and attach macro to additional_data."""
    new_conf, notes, macro_risks, macro_catalysts = _adjust_confidence(agent_key, result.confidence, macro)

    macro_block = macro.to_dict()
    add = dict(result.additional_data or {})
    add["macro"] = macro_block
    add["macro_adjustment_notes"] = notes

    reasoning = result.reasoning
    if notes:
        reasoning += "\n\nMacro context: " + "; ".join(notes)

    return replace(
        result,
        confidence=new_conf,
        reasoning=reasoning,
        risk_factors=result.risk_factors + macro_risks,
        catalysts=result.catalysts + macro_catalysts,
        additional_data=add,
    )
