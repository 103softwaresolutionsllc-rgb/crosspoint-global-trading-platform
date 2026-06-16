from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Protocol

from global_trading.agents.execution import ExecutionAgent
from global_trading.agents.market_data import MarketDataAgent
from global_trading.agents.portfolio import PortfolioAgent
from global_trading.agents.risk_agent import RiskAgent
from global_trading.core.audit import AuditLog
from global_trading.core.domain import Order, TradeIntent, Venue
from global_trading.core.ledger import PositionLedger
from global_trading.core.risk import RiskDecision
from global_trading.core.serde import to_jsonable
from global_trading.observability.metrics import Metrics


class SignalProvider(Protocol):
    def generate_demo_intent(self) -> TradeIntent: ...


class SupportsPlaceOrder(Protocol):
    def place_order(self, order: Order) -> Order: ...


@dataclass
class WorkflowResult:
    intent: TradeIntent | None
    risk: RiskDecision | None
    order: Order | None
    skipped_reason: str | None = None


class TradingWorkflow:
    """
    State machine: data → signal → portfolio → risk → execution → submit.

    Pass ``ConsensusSignalProvider`` (fincept_terminal.trading.bridge) as signal
    for live agent consensus instead of demo intents.
    """

    def __init__(
        self,
        *,
        market_data: MarketDataAgent,
        signal: SignalProvider,
        portfolio: PortfolioAgent,
        risk: RiskAgent,
        execution: ExecutionAgent,
        connector: SupportsPlaceOrder,
        venue: Venue,
        account_id: str,
        audit: AuditLog,
        ledger: PositionLedger,
        metrics: Metrics | None = None,
        liquidity_gate=None,
    ) -> None:
        self.market_data = market_data
        self.signal = signal
        self.portfolio = portfolio
        self.risk = risk
        self.execution = execution
        self.connector = connector
        self.venue = venue
        self.account_id = account_id
        self.audit = audit
        self.ledger = ledger
        self.metrics = metrics
        self.liquidity_gate = liquidity_gate

    def run_once(self) -> WorkflowResult:
        intent = self.signal.generate_demo_intent()
        mark = self.market_data.mark_price(intent.instrument)
        intent = self.portfolio.adjust_intent(intent, mark_price=mark)
        self.audit.append("intent_created", {"intent": to_jsonable(intent)})

        if self.liquidity_gate is not None:
            sym = intent.instrument.symbol
            if not self.liquidity_gate.execution_allowed(sym):
                reason = getattr(self.liquidity_gate, "pause_reason", lambda _s: "toxic flow")(sym)
                return WorkflowResult(
                    intent=intent,
                    risk=None,
                    order=None,
                    skipped_reason=f"liquidity_gate: {reason}",
                )

        decision = self.risk.check(intent, mark_price=mark)
        self.audit.append("risk_check", {"decision": asdict(decision)})
        if not decision.allowed:
            if self.metrics:
                self.metrics.inc("risk_blocks")
            return WorkflowResult(intent=intent, risk=decision, order=None, skipped_reason=decision.reason)

        qty = decision.capped_quantity if decision.capped_quantity is not None else intent.quantity
        intent = replace(intent, quantity=qty)

        order = self.execution.intent_to_order(intent, account_id=self.account_id, venue=self.venue)
        self.audit.append("order_built", {"order": to_jsonable(order)})

        placed = self.connector.place_order(order)
        self.audit.append("order_placed", {"order": to_jsonable(placed)})

        fill_price = self.market_data.mark_price(placed.instrument)
        self.ledger.apply_filled_order(placed, fill_price=fill_price)
        if self.metrics:
            self.metrics.inc("workflow_completed")
        return WorkflowResult(intent=intent, risk=decision, order=placed)
