"""VWAP and TWAP execution schedulers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class ExecutionSlice:
    quantity: float
    scheduled_at: datetime
    slice_index: int
    total_slices: int


class TWAPScheduler:
    """Time-Weighted Average Price — equal slices over a window."""

    def __init__(self, total_qty: float, num_slices: int, window_minutes: int = 60) -> None:
        self.total_qty = total_qty
        self.num_slices = max(1, num_slices)
        self.window_minutes = window_minutes

    def schedule(self, start: datetime | None = None) -> list[ExecutionSlice]:
        start = start or datetime.now()
        slice_qty = self.total_qty / self.num_slices
        interval = timedelta(minutes=self.window_minutes / self.num_slices)
        return [
            ExecutionSlice(
                quantity=slice_qty,
                scheduled_at=start + interval * i,
                slice_index=i,
                total_slices=self.num_slices,
            )
            for i in range(self.num_slices)
        ]


class VWAPScheduler:
    """Volume-Weighted Average Price — slices proportional to historical volume profile."""

    def __init__(
        self,
        total_qty: float,
        volume_profile: list[float],
        window_minutes: int = 60,
    ) -> None:
        self.total_qty = total_qty
        self.volume_profile = volume_profile or [1.0]
        self.window_minutes = window_minutes

    def schedule(self, start: datetime | None = None) -> list[ExecutionSlice]:
        start = start or datetime.now()
        total_vol = sum(self.volume_profile)
        n = len(self.volume_profile)
        interval = timedelta(minutes=self.window_minutes / n)
        slices: list[ExecutionSlice] = []
        for i, vol in enumerate(self.volume_profile):
            qty = self.total_qty * (vol / total_vol)
            slices.append(
                ExecutionSlice(
                    quantity=qty,
                    scheduled_at=start + interval * i,
                    slice_index=i,
                    total_slices=n,
                )
            )
        return slices
