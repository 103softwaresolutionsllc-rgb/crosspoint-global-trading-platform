"""Tests for IPO opportunity screener."""

from __future__ import annotations

import pytest

from fincept_terminal.agents.macro_context import _fallback_snapshot
from fincept_terminal.agents.orchestration.ipo_screener import (
    IPO_PIPELINE,
    _heuristic_votes,
    _votes_to_score,
    screen_ipo_opportunities,
)


def test_heuristic_votes_produce_scores():
    macro = _fallback_snapshot()
    c = IPO_PIPELINE[0]  # Stripe upcoming
    votes = _heuristic_votes(c, macro)
    assert len(votes) == 4
    score = _votes_to_score(votes)
    assert -2.0 <= score <= 2.0


@pytest.mark.asyncio
async def test_screen_returns_ranked_suggestions():
    macro = _fallback_snapshot()
    results = await screen_ipo_opportunities(macro, min_score=0.0, max_live_consensus=0)
    assert len(results) > 0
    scores = [r.composite_score for r in results]
    assert scores == sorted(scores, reverse=True)
    assert all(r.entry_note for r in results)
