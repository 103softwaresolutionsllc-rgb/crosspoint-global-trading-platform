import pytest

from fincept_terminal.agents.orchestration.consensus import (
    AgentConsensus,
    _score_to_recommendation,
)
from fincept_terminal.agents.base import Recommendation


def test_score_to_recommendation_mapping() -> None:
    assert _score_to_recommendation(2.0) == Recommendation.STRONG_BUY
    assert _score_to_recommendation(0.8) == Recommendation.BUY
    assert _score_to_recommendation(0.0) == Recommendation.HOLD
    assert _score_to_recommendation(-0.8) == Recommendation.SELL


@pytest.mark.asyncio
async def test_consensus_analyze_single_ticker() -> None:
    consensus = AgentConsensus()
    result = await consensus.analyze("AAPL")
    assert result.ticker == "AAPL"
    assert len(result.agent_results) >= 1
    assert -2.0 <= result.consensus_score <= 2.0
