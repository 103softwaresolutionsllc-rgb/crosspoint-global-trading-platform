from __future__ import annotations

import threading
from collections import defaultdict


class Metrics:
    """Thread-safe in-process counters and histograms (replace with Prometheus later)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[str, float] = defaultdict(float)
        self._histograms: dict[str, list[float]] = defaultdict(list)

    def inc(self, name: str, value: float = 1.0) -> None:
        with self._lock:
            self._counters[name] += value

    def observe(self, name: str, value: float) -> None:
        with self._lock:
            self._histograms[name].append(value)

    def snapshot(self) -> dict[str, float]:
        with self._lock:
            out = dict(self._counters)
            for name, values in self._histograms.items():
                if values:
                    sorted_v = sorted(values)
                    n = len(sorted_v)
                    out[f"{name}_count"] = n
                    out[f"{name}_p50"] = sorted_v[n // 2]
                    out[f"{name}_p95"] = sorted_v[int(n * 0.95)]
            return out
