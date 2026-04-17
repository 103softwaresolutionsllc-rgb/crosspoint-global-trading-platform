from __future__ import annotations

import threading
from collections import defaultdict


class Metrics:
    """Thread-safe in-process counters (replace with Prometheus/OpenTelemetry later)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[str, float] = defaultdict(float)

    def inc(self, name: str, value: float = 1.0) -> None:
        with self._lock:
            self._counters[name] += value

    def snapshot(self) -> dict[str, float]:
        with self._lock:
            return dict(self._counters)
