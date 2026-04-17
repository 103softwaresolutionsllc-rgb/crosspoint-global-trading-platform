from global_trading.agents.execution import ExecutionAgent
from global_trading.agents.market_data import MarketDataAgent
from global_trading.agents.portfolio import PortfolioAgent
from global_trading.agents.risk_agent import RiskAgent
from global_trading.agents.signal import SignalAgent
from global_trading.connectors.fake import FakeConnector
from global_trading.core.audit import AuditLog
from global_trading.core.domain import OrderStatus, Venue
from global_trading.core.ledger import PositionLedger
from global_trading.core.risk import RiskConfig, RiskEngine
from global_trading.observability.metrics import Metrics
from global_trading.orchestrator.workflow import TradingWorkflow


def test_run_once_fake() -> None:
    audit = AuditLog(db_path=":memory:")
    audit.init()
    metrics = Metrics()
    ledger = PositionLedger(account_id="paper-1")
    risk = RiskAgent(RiskEngine(RiskConfig(max_notional_per_order=1_000_000.0)))
    wf = TradingWorkflow(
        market_data=MarketDataAgent(marks={"DEMO": 10.0}),
        signal=SignalAgent(),
        portfolio=PortfolioAgent(),
        risk=risk,
        execution=ExecutionAgent(),
        connector=FakeConnector(account_id="paper-1", metrics=metrics),
        venue=Venue.BROKER_GENERIC,
        account_id="paper-1",
        audit=audit,
        ledger=ledger,
        metrics=metrics,
    )
    result = wf.run_once()
    assert result.order is not None
    assert result.order.status == OrderStatus.FILLED
