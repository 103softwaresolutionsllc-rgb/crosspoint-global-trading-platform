"""Signal-to-fill latency tracking."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

from global_trading.observability.metrics import Metrics


@dataclass
class LatencyRecord:
    intent_id: UUID
    signal_at: datetime
    fill_at: datetime | None = None
    latency_ms: float | None = None


class LatencyTracker:
    """Track time from signal generation to order fill."""

    def __init__(self, metrics: Metrics | None = None) -> None:
        self._pending: dict[UUID, float] = {}
        self._records: list[LatencyRecord] = []
        self.metrics = metrics

    def mark_signal(self, intent_id: UUID) -> None:
        self._pending[intent_id] = time.perf_counter()

    def mark_fill(self, intent_id: UUID) -> LatencyRecord | None:
        start = self._pending.pop(intent_id, None)
        if start is None:
            return None
        elapsed_ms = (time.perf_counter() - start) * 1000
        record = LatencyRecord(
            intent_id=intent_id,
            signal_at=datetime.now(UTC),
            fill_at=datetime.now(UTC),
            latency_ms=elapsed_ms,
        )
        self._records.append(record)
        if self.metrics:
            self.metrics.observe("signal_to_fill_ms", elapsed_ms)
        return record

    def summary(self) -> dict[str, float]:
        latencies = [r.latency_ms for r in self._records if r.latency_ms is not None]
        if not latencies:
            return {"count": 0, "p50_ms": 0, "p95_ms": 0, "max_ms": 0}
        sorted_lat = sorted(latencies)
        n = len(sorted_lat)
        return {
            "count": n,
            "p50_ms": sorted_lat[n // 2],
            "p95_ms": sorted_lat[int(n * 0.95)],
            "max_ms": sorted_lat[-1],
        }
