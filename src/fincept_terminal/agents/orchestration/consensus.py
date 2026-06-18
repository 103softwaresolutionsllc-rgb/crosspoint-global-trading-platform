"""
Multi-agent consensus scoring across Buffett, Graham, Lynch, and Dunlap agents.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Sequence

from fincept_terminal.agents.base import AgentResult, Recommendation
from fincept_terminal.agents.orchestration.debate import run_debate_matrix
from fincept_terminal.agents.macro_context import get_macro_context
from fincept_terminal.agents.value_investors.buffett import BuffettAgent
from fincept_terminal.agents.value_investors.dunlap import IanDunlapAgent
from fincept_terminal.agents.value_investors.graham import GrahamAgent
from fincept_terminal.agents.value_investors.lynch import LynchAgent
from fincept_terminal.agents.quant_agents.simons import SimonsAgent

_RECOMMENDATION_SCORES: dict[Recommendation, float] = {
    Recommendation.STRONG_BUY: 2.0,
    Recommendation.BUY: 1.0,
    Recommendation.HOLD: 0.0,
    Recommendation.SELL: -1.0,
    Recommendation.STRONG_SELL: -2.0,
}

DEFAULT_AGENT_WEIGHTS: dict[str, float] = {
    "Warren Buffett": 1.0,
    "Benjamin Graham": 1.0,
    "Peter Lynch": 1.0,
    "Ian Dunlap": 1.0,
    "Jim Simons": 1.0,
}


@dataclass
class ConsensusResult:
    ticker: str
    consensus_score: float
    consensus_recommendation: Recommendation
    agent_results: list[AgentResult] = field(default_factory=list)
    agreement_pct: float = 0.0
    dissenting_agents: list[str] = field(default_factory=list)

    @property
    def is_buy_consensus(self) -> bool:
        return self.consensus_score >= 1.0

    @property
    def is_strong_buy_consensus(self) -> bool:
        return self.consensus_score >= 1.5


def _score_to_recommendation(score: float) -> Recommendation:
    if score >= 1.5:
        return Recommendation.STRONG_BUY
    if score >= 0.5:
        return Recommendation.BUY
    if score <= -1.5:
        return Recommendation.STRONG_SELL
    if score <= -0.5:
        return Recommendation.SELL
    return Recommendation.HOLD


class AgentConsensus:
    """Run all value-investor agents on a ticker and produce a weighted consensus."""

    def __init__(
        self,
        weights: dict[str, float] | None = None,
        *,
        enable_debate: bool = True,
    ) -> None:
        self.weights = weights or DEFAULT_AGENT_WEIGHTS
        self.enable_debate = enable_debate
        self._agents = [
            BuffettAgent(),
            GrahamAgent(),
            LynchAgent(),
            IanDunlapAgent(),
            SimonsAgent(),
        ]

    async def analyze(self, ticker: str, *, macro=None) -> ConsensusResult:
        macro_ctx = macro if macro is not None else await get_macro_context()
        results = await asyncio.gather(
            *[agent.analyze(ticker, macro=macro_ctx) for agent in self._agents],
            return_exceptions=True,
        )

        valid: list[AgentResult] = []
        for r in results:
            if isinstance(r, AgentResult):
                valid.append(r)

        if valid:
            valid = await self._apply_regime_checks(valid, ticker)

        if self.enable_debate and valid:
            debate = run_debate_matrix(valid, ticker)
            valid = debate.results

        if not valid:
            return ConsensusResult(
                ticker=ticker,
                consensus_score=0.0,
                consensus_recommendation=Recommendation.HOLD,
            )

        weighted_sum = 0.0
        weight_total = 0.0
        for result in valid:
            w = self.weights.get(result.agent_name, 1.0)
            base = _RECOMMENDATION_SCORES.get(result.recommendation, 0.0)
            weighted_sum += base * result.confidence * w
            weight_total += w

        score = weighted_sum / weight_total if weight_total else 0.0
        consensus_rec = _score_to_recommendation(score)

        buy_votes = sum(
            1 for r in valid if r.recommendation in (Recommendation.BUY, Recommendation.STRONG_BUY)
        )
        agreement = buy_votes / len(valid) if valid else 0.0

        dissenting = [
            r.agent_name
            for r in valid
            if _RECOMMENDATION_SCORES.get(r.recommendation, 0.0) * r.confidence < 0
            and score >= 0.5
        ]

        return ConsensusResult(
            ticker=ticker,
            consensus_score=score,
            consensus_recommendation=consensus_rec,
            agent_results=valid,
            agreement_pct=agreement,
            dissenting_agents=dissenting,
        )

    async def _apply_regime_checks(
        self, results: list[AgentResult], ticker: str
    ) -> list[AgentResult]:
        """Structural variance dampening before debate/consensus aggregation."""
        import yfinance as yf

        try:
            hist = yf.Ticker(ticker).history(period="1y")
            if hist.empty or not self._agents:
                return results
            probe = self._agents[0]
            regime = await probe._structural_regime_check(ticker, hist)
            return [probe._apply_structural_dampening(r, regime) for r in results]
        except Exception:
            return results

    async def analyze_batch(
        self, tickers: Sequence[str], *, min_score: float = 0.5
    ) -> list[ConsensusResult]:
        results = await asyncio.gather(*[self.analyze(t) for t in tickers])
        return [r for r in results if r.consensus_score >= min_score]
