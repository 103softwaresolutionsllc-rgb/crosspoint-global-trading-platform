"""
Celery tasks for scheduled agent screening and consensus runs.

Start worker: celery -A fincept_terminal.scheduler.tasks worker --loglevel=info
Start beat:    celery -A fincept_terminal.scheduler.tasks beat --loglevel=info
"""

from __future__ import annotations

import asyncio
import os

try:
    from celery import Celery
    from celery.schedules import crontab
except ImportError:
    Celery = None  # type: ignore[misc, assignment]

broker_url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")

if Celery is not None:
    app = Celery("crosspoint", broker=broker_url, backend=broker_url)
    app.conf.beat_schedule = {
        "refresh-macro-cache": {
            "task": "fincept_terminal.scheduler.tasks.refresh_macro_cache",
            "schedule": crontab(hour=5, minute=45),
        },
        "nightly-watchlist-screen": {
            "task": "fincept_terminal.scheduler.tasks.run_watchlist_screen",
            "schedule": crontab(hour=6, minute=0),
            "kwargs": {"tickers": ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN"]},
        },
    }
else:
    app = None  # type: ignore[assignment]


def _run_async(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


if app is not None:

    @app.task(name="fincept_terminal.scheduler.tasks.refresh_macro_cache")
    def refresh_macro_cache() -> dict:
        from fincept_terminal.agents.macro_context import get_macro_context

        snapshot = _run_async(get_macro_context(force_refresh=True))
        return snapshot.to_dict()

    @app.task(name="fincept_terminal.scheduler.tasks.run_watchlist_screen")
    def run_watchlist_screen(tickers: list[str], min_consensus: float = 0.5) -> dict:
        from fincept_terminal.agents.orchestration.screener import AgentScreener

        screener = AgentScreener(min_consensus_score=min_consensus)
        result = _run_async(screener.screen(tickers))
        return {
            "passed": [
                {"ticker": r.ticker, "score": r.consensus_score} for r in result.passed
            ],
            "failed": result.failed,
            "errors": result.errors,
        }

    @app.task(name="fincept_terminal.scheduler.tasks.run_consensus")
    def run_consensus(ticker: str) -> dict:
        from fincept_terminal.agents.orchestration.consensus import AgentConsensus

        result = _run_async(AgentConsensus().analyze(ticker))
        return {
            "ticker": result.ticker,
            "score": result.consensus_score,
            "recommendation": result.consensus_recommendation.value,
        }
