import pytest

from fincept_terminal.agents.macro_agents.dalio import DalioAgent
from fincept_terminal.agents.base import AgentResult, Recommendation


def test_dalio_agent_initialization() -> None:
    agent = DalioAgent()
    assert agent.name == "Ray Dalio"
    assert agent.agent_type.value == "macro_agent"


@pytest.mark.asyncio
async def test_dalio_agent_analyze_aapl() -> None:
    agent = DalioAgent()
    result = await agent.analyze("AAPL")

    assert isinstance(result, AgentResult)
    assert result.agent_name == "Ray Dalio"
    assert result.ticker == "AAPL"
    assert isinstance(result.recommendation, Recommendation)
    assert 0.0 <= result.confidence <= 1.0
    assert len(result.reasoning) > 0

    # Check key metrics are present
    assert "debt_to_equity" in result.key_metrics
    assert "beta" in result.key_metrics
    assert "dividend_yield" in result.key_metrics
    assert "current_ratio" in result.key_metrics
    assert "operating_margin" in result.key_metrics
    assert "pe_ratio" in result.key_metrics
    assert "interest_coverage" in result.key_metrics
    assert "margin_stability" in result.key_metrics
    assert "regime_alignment_score" in result.key_metrics
    assert "debt_safety_score" in result.key_metrics
    assert "risk_parity_score" in result.key_metrics
    assert "intrinsic_value" in result.key_metrics
    assert "margin_of_safety" in result.key_metrics
