import pytest

from fincept_terminal.agents.base import AgentResult, Recommendation
from fincept_terminal.agents.macro_context import (
    MacroSnapshot,
    apply_macro_to_result,
    detect_regime,
    fetch_macro_snapshot,
    get_macro_context,
    invalidate_macro_cache,
)


def test_detect_regime_late_cycle() -> None:
    assert detect_regime(gdp_growth=2.0, cpi_yoy=3.2, unemployment=4.1, yield_curve=-0.15) == "late_cycle"


def test_detect_regime_expansion() -> None:
    assert detect_regime(gdp_growth=3.0, cpi_yoy=2.5, unemployment=3.8, yield_curve=0.5) == "expansion"


def test_apply_macro_buffett_inverted_curve() -> None:
    macro = MacroSnapshot(
        gdp_growth_yoy=2.1,
        cpi_yoy=3.2,
        unemployment=4.1,
        fed_funds_rate=5.33,
        yield_curve_10y2y=-0.15,
        regime="late_cycle",
        as_of="demo",
    )
    base = AgentResult(
        agent_name="Warren Buffett",
        ticker="AAPL",
        recommendation=Recommendation.BUY,
        confidence=0.82,
        reasoning="Base case",
        key_metrics={},
        risk_factors=[],
        catalysts=[],
    )
    adjusted = apply_macro_to_result(base, macro, "buffett")
    assert adjusted.confidence < base.confidence
    assert adjusted.additional_data is not None
    assert "macro" in adjusted.additional_data
    assert adjusted.additional_data["macro"]["regime"] == "late_cycle"


@pytest.mark.asyncio
async def test_fetch_macro_fallback_without_api_key() -> None:
    invalidate_macro_cache()
    snap = await fetch_macro_snapshot(api_key="")
    assert snap.source == "fallback"
    assert snap.regime == "late_cycle"


@pytest.mark.asyncio
async def test_get_macro_context_caches() -> None:
    invalidate_macro_cache()
    a = await get_macro_context()
    b = await get_macro_context()
    assert a.regime == b.regime
