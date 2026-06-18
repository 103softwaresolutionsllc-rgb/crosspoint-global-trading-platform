import pytest

from fincept_terminal.agents.quant_agents.simons import SimonsAgent
from fincept_terminal.agents.base import AgentResult, Recommendation


def test_simons_agent_initialization() -> None:
    agent = SimonsAgent()
    assert agent.name == "Jim Simons"
    assert agent.agent_type.value == "quant_agent"


@pytest.mark.asyncio
async def test_simons_agent_analyze_aapl() -> None:
    agent = SimonsAgent()
    result = await agent.analyze("AAPL")
    
    assert isinstance(result, AgentResult)
    assert result.agent_name == "Jim Simons"
    assert result.ticker == "AAPL"
    assert isinstance(result.recommendation, Recommendation)
    assert 0.0 <= result.confidence <= 1.0
    assert len(result.reasoning) > 0
    
    # Check that the calculated technical indicators and scores are present
    assert 'rsi' in result.key_metrics
    assert 'macd' in result.key_metrics
    assert 'bb_position' in result.key_metrics
    assert 'momentum_score' in result.key_metrics
    assert 'reversion_score' in result.key_metrics
    assert 'volatility_dampening' in result.key_metrics
    assert 'z_score' in result.key_metrics
    assert 'vol_ratio' in result.key_metrics
