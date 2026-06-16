"""
IPO opportunity screener — agent-aligned early-entry suggestions.

For tradeable recent IPOs, runs live AgentConsensus. For pre-IPO names,
applies each value agent's criteria as deterministic proxies, then aggregates
with the same weighted scoring used in consensus.py.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import yfinance as yf

from fincept_terminal.agents.base import Recommendation
from fincept_terminal.agents.macro_context import MacroSnapshot, get_macro_context
from fincept_terminal.agents.orchestration.consensus import (
    DEFAULT_AGENT_WEIGHTS,
    AgentConsensus,
    _RECOMMENDATION_SCORES,
    _score_to_recommendation,
)

_REC_SCORES = _RECOMMENDATION_SCORES


@dataclass
class IpoCandidate:
    company: str
    ticker: str | None
    status: str  # upcoming | recent | open
    sector: str
    est_window: str
    growth_profile: str  # high | moderate | low
    profitable: bool
    moat_hint: str  # strong | moderate | weak
    notes: str = ""


@dataclass
class AgentIpoVote:
    agent: str
    endorsement: str  # strong | watch | pass
    confidence: float
    rationale: str


@dataclass
class IpoSuggestion:
    company: str
    ticker: str | None
    status: str
    sector: str
    est_window: str
    composite_score: float
    recommendation: str
    leading_agents: list[str]
    agent_votes: list[AgentIpoVote]
    entry_note: str
    macro_fit: str = ""


# Curated pipeline — swap via config/workflow later
IPO_PIPELINE: list[IpoCandidate] = [
    IpoCandidate("Stripe", None, "upcoming", "Fintech", "2026 H1", "high", True, "strong",
                 "Payments infra · recurring revenue · late-stage private"),
    IpoCandidate("Databricks", None, "upcoming", "AI / Data", "2026 H1", "high", False, "strong",
                 "Lakehouse category leader · high growth pre-profit"),
    IpoCandidate("Discord", None, "upcoming", "Social / Gaming", "2026 H2", "high", False, "moderate",
                 "Community platform · monetization ramp"),
    IpoCandidate("Astera Labs", "ALAB", "recent", "Semiconductors", "IPO Mar 2024", "high", False, "strong",
                 "AI connectivity · post-IPO entry window"),
    IpoCandidate("Reddit", "RDDT", "open", "Social Media", "IPO Mar 2024", "high", False, "moderate",
                 "User growth · ad model scaling"),
    IpoCandidate("Rubrik", "RBRK", "recent", "Cybersecurity", "IPO Apr 2024", "high", False, "strong",
                 "Data security · enterprise SaaS"),
    IpoCandidate("Lineage", "LINE", "recent", "Logistics REIT", "IPO Jul 2024", "moderate", True, "moderate",
                 "Cold-storage moat · yield-oriented"),
    IpoCandidate("Waystar", "WAY", "recent", "Health IT", "IPO Jun 2024", "moderate", True, "moderate",
                 "Healthcare payments · sticky workflows"),
]


def _buffett_ipo_vote(c: IpoCandidate, macro: MacroSnapshot) -> AgentIpoVote:
    score = 0.4
    if c.profitable:
        score += 0.25
    if c.moat_hint == "strong":
        score += 0.25
    elif c.moat_hint == "moderate":
        score += 0.1
    if c.status == "upcoming" and not c.profitable:
        score -= 0.15
    if macro.regime == "recession_risk":
        score -= 0.1
    score = max(0.0, min(1.0, score))
    end = "strong" if score >= 0.7 else "watch" if score >= 0.5 else "pass"
    return AgentIpoVote(
        "Buffett",
        end,
        score,
        "Favors profitable compounders with durable moats; cautious on pre-profit IPO hype.",
    )


def _graham_ipo_vote(c: IpoCandidate, macro: MacroSnapshot) -> AgentIpoVote:
    score = 0.35
    if c.profitable:
        score += 0.3
    if c.growth_profile == "low":
        score += 0.15
    if c.status in ("upcoming", "recent"):
        score -= 0.1  # IPOs rarely offer net-net margin of safety
    if macro.cpi_yoy and macro.cpi_yoy > 4:
        score -= 0.05
    score = max(0.0, min(1.0, score))
    end = "strong" if score >= 0.65 else "watch" if score >= 0.45 else "pass"
    return AgentIpoVote(
        "Graham",
        end,
        score,
        "Needs tangible margin of safety; most IPOs price above intrinsic value on day one.",
    )


def _lynch_ipo_vote(c: IpoCandidate, macro: MacroSnapshot) -> AgentIpoVote:
    score = 0.45
    if c.growth_profile == "high":
        score += 0.3
    if c.sector in ("AI / Data", "Semiconductors", "Fintech", "Cybersecurity"):
        score += 0.15
    if c.status == "upcoming":
        score += 0.05  # Lynch likes getting in early on growth stories
    if macro.regime == "expansion":
        score += 0.1
    score = max(0.0, min(1.0, score))
    end = "strong" if score >= 0.7 else "watch" if score >= 0.5 else "pass"
    return AgentIpoVote(
        "Lynch",
        end,
        score,
        "Prefers understandable growth at reasonable price; IPOs OK if story is clear.",
    )


def _dunlap_ipo_vote(c: IpoCandidate, macro: MacroSnapshot) -> AgentIpoVote:
    score = 0.4
    if c.moat_hint == "strong" and c.growth_profile == "high":
        score += 0.25
    if c.profitable:
        score += 0.15
    if c.status == "upcoming" and c.growth_profile == "high":
        score += 0.1
    if macro.regime == "stagflation":
        score -= 0.15
    score = max(0.0, min(1.0, score))
    end = "strong" if score >= 0.68 else "watch" if score >= 0.48 else "pass"
    return AgentIpoVote(
        "Dunlap",
        end,
        score,
        "Targets elite compounders early; needs path to operational leverage post-IPO.",
    )


def _heuristic_votes(c: IpoCandidate, macro: MacroSnapshot) -> list[AgentIpoVote]:
    return [
        _buffett_ipo_vote(c, macro),
        _graham_ipo_vote(c, macro),
        _lynch_ipo_vote(c, macro),
        _dunlap_ipo_vote(c, macro),
    ]


def _votes_to_score(votes: list[AgentIpoVote]) -> float:
    weighted = 0.0
    total_w = 0.0
    for v in votes:
        full = {s: f for f, s in _AGENT_SHORT.items()}.get(v.agent, v.agent)
        w = DEFAULT_AGENT_WEIGHTS.get(full, 1.0)
        if v.endorsement == "strong":
            base = 1.5
        elif v.endorsement == "watch":
            base = 0.5
        else:
            base = -0.5
        weighted += base * v.confidence * w
        total_w += w
    return weighted / total_w if total_w else 0.0


def _entry_note(c: IpoCandidate, score: float, rec: str) -> str:
    if c.status == "upcoming":
        if score >= 0.8:
            return "Allocate to pre-IPO secondary / directed listing watch — high agent alignment."
        if score >= 0.5:
            return "Add to IPO calendar alert — wait for S-1 pricing and first-day lock-up map."
        return "Monitor only — agents see weak early-entry edge vs pricing risk."
    if c.status == "recent":
        if score >= 0.8:
            return "Post-IPO dip entry — consider scaled VWAP over 5–10 sessions."
        return "Tradeable now — use VaR-sized starter position; avoid chase on day-one gaps."
    if score >= 0.7:
        return "Open market entry — consensus supports adding on pullbacks to 20DMA."
    return "Hold watchlist — let agents re-score after next earnings / lock-up expiry."


_AGENT_SHORT = {
    "Warren Buffett": "Buffett",
    "Benjamin Graham": "Graham",
    "Peter Lynch": "Lynch",
    "Ian Dunlap": "Dunlap",
}


async def _live_consensus_votes(ticker: str, macro: MacroSnapshot) -> list[AgentIpoVote]:
    """Map live AgentConsensus results to IPO vote format."""
    result = await AgentConsensus(enable_debate=True).analyze(ticker, macro=macro)
    votes: list[AgentIpoVote] = []
    for ar in result.agent_results:
        short = _AGENT_SHORT.get(ar.agent_name, ar.agent_name)
        if ar.recommendation in (Recommendation.STRONG_BUY, Recommendation.BUY):
            end = "strong"
        elif ar.recommendation == Recommendation.HOLD:
            end = "watch"
        else:
            end = "pass"
        votes.append(
            AgentIpoVote(
                short,
                end,
                ar.confidence,
                ar.reasoning[:120] + ("…" if len(ar.reasoning) > 120 else ""),
            )
        )
    return votes


def _ticker_tradeable(ticker: str) -> bool:
    try:
        hist = yf.Ticker(ticker).history(period="5d")
        return not hist.empty
    except Exception:
        return False


async def screen_ipo_opportunities(
    macro: MacroSnapshot | None = None,
    *,
    min_score: float = 0.3,
    max_live_consensus: int = 3,
) -> list[IpoSuggestion]:
    """Rank IPO pipeline by agent-aligned composite scores."""
    macro_ctx = macro or await get_macro_context()
    suggestions: list[IpoSuggestion] = []
    live_calls = 0

    for c in IPO_PIPELINE:
        votes: list[AgentIpoVote]
        if c.ticker and _ticker_tradeable(c.ticker) and live_calls < max_live_consensus:
            try:
                votes = await _live_consensus_votes(c.ticker, macro_ctx)
                live_calls += 1
            except Exception:
                votes = _heuristic_votes(c, macro_ctx)
        else:
            votes = _heuristic_votes(c, macro_ctx)

        score = _votes_to_score(votes)
        if score < min_score:
            continue

        rec = _score_to_recommendation(score).value
        leading = [v.agent for v in votes if v.endorsement == "strong"]
        macro_fit = f"{macro_ctx.regime} · {macro_ctx.pill_text()}"

        suggestions.append(
            IpoSuggestion(
                company=c.company,
                ticker=c.ticker,
                status=c.status,
                sector=c.sector,
                est_window=c.est_window,
                composite_score=round(score, 2),
                recommendation=rec,
                leading_agents=leading,
                agent_votes=votes,
                entry_note=_entry_note(c, score, rec),
                macro_fit=macro_fit,
            )
        )

    suggestions.sort(key=lambda s: s.composite_score, reverse=True)
    return suggestions


def fetch_ipo_suggestions_sync(macro: MacroSnapshot | None = None) -> list[IpoSuggestion]:
    """Synchronous wrapper for dashboard loaders."""
    try:
        return asyncio.run(screen_ipo_opportunities(macro))
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(screen_ipo_opportunities(macro))
        finally:
            loop.close()
