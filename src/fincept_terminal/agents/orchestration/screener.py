"""
Multi-ticker batch screening pipeline using agent consensus.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from fincept_terminal.agents.macro_context import get_macro_context
from fincept_terminal.agents.orchestration.consensus import AgentConsensus, ConsensusResult


@dataclass
class ScreenResult:
    watchlist: list[str]
    passed: list[ConsensusResult] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    errors: dict[str, str] = field(default_factory=dict)

    @property
    def pass_rate(self) -> float:
        if not self.watchlist:
            return 0.0
        return len(self.passed) / len(self.watchlist)


class AgentScreener:
    """Screen a watchlist through the four-agent consensus pipeline."""

    def __init__(
        self,
        *,
        min_consensus_score: float = 0.5,
        max_concurrency: int = 4,
    ) -> None:
        self.min_consensus_score = min_consensus_score
        self.max_concurrency = max_concurrency
        self.consensus = AgentConsensus()

    async def screen(self, tickers: list[str]) -> ScreenResult:
        result = ScreenResult(watchlist=tickers)
        sem = asyncio.Semaphore(self.max_concurrency)
        macro = await get_macro_context()

        async def _screen_one(ticker: str) -> None:
            async with sem:
                try:
                    consensus = await self.consensus.analyze(ticker, macro=macro)
                    if consensus.consensus_score >= self.min_consensus_score:
                        result.passed.append(consensus)
                    else:
                        result.failed.append(ticker)
                except Exception as e:
                    result.errors[ticker] = str(e)
                    result.failed.append(ticker)

        await asyncio.gather(*[_screen_one(t) for t in tickers])
        result.passed.sort(key=lambda r: r.consensus_score, reverse=True)
        return result
