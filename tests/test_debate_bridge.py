"""Tests for agent debate matrix, liquidity gate, and consensus bridge."""

from __future__ import annotations

import pytest

from fincept_terminal.agents.base import AgentResult, Recommendation
from fincept_terminal.agents.liquidity_gate import LiquidityGateAgent
from fincept_terminal.agents.orchestration.debate import run_debate_matrix
from fincept_terminal.trading.bridge import BridgeConfig, ConsensusSignalBridge
from fincept_terminal.trading.websocket import OrderBookData
from datetime import datetime, UTC


def _result(name: str, rec: Recommendation, conf: float, **metrics) -> AgentResult:
    return AgentResult(
        agent_name=name,
        ticker="AAPL",
        recommendation=rec,
        confidence=conf,
        reasoning="test",
        key_metrics=metrics,
        risk_factors=[],
        catalysts=[],
    )


def test_debate_appends_counter_argument():
    results = [
        _result("Benjamin Graham", Recommendation.BUY, 0.8, margin_of_safety=0.3),
        _result("Peter Lynch", Recommendation.HOLD, 0.6, peg_ratio=2.0),
        _result("Warren Buffett", Recommendation.HOLD, 0.5),
        _result("Ian Dunlap", Recommendation.HOLD, 0.5),
    ]
    debate = run_debate_matrix(results, "AAPL")
    graham = next(r for r in debate.results if r.agent_name == "Benjamin Graham")
    assert any("Debate" in risk for risk in graham.risk_factors)
    assert graham.confidence < 0.8


def test_liquidity_gate_pauses_on_wide_spread():
    gate = LiquidityGateAgent()
    book = OrderBookData(
        symbol="AAPL",
        timestamp=datetime.now(UTC),
        bids=[[100.0, 500.0]],
        asks=[[100.02, 500.0]],
    )
    snap = gate.on_order_book(book)
    assert snap.spread_bps > 0
    assert gate.execution_allowed("AAPL") is True

    toxic = OrderBookData(
        symbol="AAPL",
        timestamp=datetime.now(UTC),
        bids=[[100.0, 5.0]],
        asks=[[101.0, 5.0]],
    )
    for _ in range(5):
        gate.on_order_book(toxic)
    assert gate.execution_allowed("AAPL") is False


@pytest.mark.asyncio
async def test_bridge_blocks_low_consensus(monkeypatch):
    from fincept_terminal.agents.orchestration import consensus as consensus_mod

    class _StubConsensus:
        async def analyze(self, ticker, *, macro=None):
            from fincept_terminal.agents.orchestration.consensus import ConsensusResult

            return ConsensusResult(
                ticker=ticker,
                consensus_score=0.2,
                consensus_recommendation=Recommendation.HOLD,
            )

    bridge = ConsensusSignalBridge(
        config=BridgeConfig(min_consensus_score=0.5),
        consensus=_StubConsensus(),
    )
    from fincept_terminal.agents.macro_context import _fallback_snapshot

    result = await bridge.evaluate("AAPL", macro=_fallback_snapshot())
    assert result.intent is None
    assert "below" in (result.skipped_reason or "")
