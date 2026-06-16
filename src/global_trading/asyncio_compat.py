"""Asyncio helpers for mixing agent coroutines with ib_insync in one process."""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import TypeVar

T = TypeVar("T")


def ensure_event_loop() -> asyncio.AbstractEventLoop:
    """Return a usable event loop (create one if asyncio.run closed it)."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("event loop is closed")
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop


def run_coro(coro: Coroutine[object, object, T]) -> T:
    """Run a coroutine without breaking subsequent ib_insync calls."""
    loop = ensure_event_loop()
    return loop.run_until_complete(coro)
