from datetime import datetime

import pytest

from global_trading.execution.algorithms import TWAPScheduler, VWAPScheduler
from global_trading.execution.benchmark import ExecutionBenchmark
from global_trading.execution.slippage import SlippageConfig, apply_slippage, estimate_slippage
from global_trading.execution.sor import BrokerScore, SmartOrderRouter
from global_trading.observability.metrics import Metrics


def test_slippage_buy_increases_price() -> None:
    price = apply_slippage(100.0, side="buy", config=SlippageConfig(bps=10))
    assert price > 100.0


def test_twap_scheduler_slices() -> None:
    scheduler = TWAPScheduler(total_qty=100, num_slices=4, window_minutes=60)
    slices = scheduler.schedule(start=datetime(2024, 1, 1, 9, 30))
    assert len(slices) == 4
    assert sum(s.quantity for s in slices) == pytest.approx(100.0)


def test_vwap_scheduler_proportional() -> None:
    scheduler = VWAPScheduler(total_qty=100, volume_profile=[1, 2, 1])
    slices = scheduler.schedule()
    assert len(slices) == 3
    assert slices[1].quantity > slices[0].quantity


def test_sor_selects_best_broker() -> None:
    router = SmartOrderRouter()
    router._scores = {
        "a": BrokerScore("a", latency_ms=100, fill_rate=0.9),
        "b": BrokerScore("b", latency_ms=10, fill_rate=0.99),
    }
    assert router.select_broker() == "b"


def test_execution_benchmark_slippage_bps() -> None:
    bench = ExecutionBenchmark(arrival_price=100.0, fill_price=100.05, quantity=10, side="buy")
    assert bench.slippage_bps == pytest.approx(5.0)


def test_latency_tracker_metrics() -> None:
    from uuid import uuid4

    from global_trading.execution.latency import LatencyTracker

    metrics = Metrics()
    tracker = LatencyTracker(metrics=metrics)
    intent_id = uuid4()
    tracker.mark_signal(intent_id)
    record = tracker.mark_fill(intent_id)
    assert record is not None
    assert record.latency_ms is not None
    snap = metrics.snapshot()
    assert snap.get("signal_to_fill_ms_count", 0) >= 1
