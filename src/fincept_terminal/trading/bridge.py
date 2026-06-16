"""
Consensus → TradeIntent bridge with macro and liquidity gating.

Replaces demo signal generation with live agent consensus, FRED regime checks,
k-NN outlier sizing, and optional toxic-flow pause from LiquidityGateAgent.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from fincept_terminal.agents.base import Recommendation
from fincept_terminal.agents.liquidity_gate import LiquidityGateAgent
from fincept_terminal.agents.macro_context import MacroSnapshot, get_macro_context
from fincept_terminal.agents.orchestration.consensus import AgentConsensus, ConsensusResult
from fincept_terminal.analytics.portfolio import knn_position_scale
from global_trading.asyncio_compat import ensure_event_loop, run_coro
from global_trading.core.domain import AssetClass, InstrumentId, OrderSide, OrderType, TradeIntent, Venue
from global_trading.instruments import (
    analysis_ticker,
    apply_env_defaults,
    apply_spec_to_env,
    parse_instrument_token,
    to_instrument_id,
)
from global_trading.settings import load_settings


@dataclass
class BridgeConfig:
    min_consensus_score: float = 0.5
    base_quantity: float = 100.0
    portfolio_value: float = 100_000.0
    blocked_regimes: tuple[str, ...] = ("recession_risk", "stagflation")
    require_liquidity_clear: bool = True


@dataclass
class BridgeResult:
    intent: TradeIntent | None
    consensus: ConsensusResult | None
    macro: MacroSnapshot | None
    knn_scale: float
    liquidity_paused: bool
    skipped_reason: str | None = None


class ConsensusSignalBridge:
    """Maps debated consensus + macro filters → sized TradeIntent."""

    def __init__(
        self,
        config: BridgeConfig | None = None,
        *,
        consensus: AgentConsensus | None = None,
        liquidity_gate: LiquidityGateAgent | None = None,
    ) -> None:
        settings = load_settings()
        self.config = config or BridgeConfig(
            portfolio_value=float(os.environ.get("GTP_PORTFOLIO_VALUE", "100000")),
            base_quantity=float(os.environ.get("GTP_BASE_ORDER_QTY", "100")),
            blocked_regimes=("recession_risk", "stagflation") if not settings.kill_switch else ("recession_risk", "stagflation"),
        )
        self.consensus = consensus or AgentConsensus(enable_debate=True)
        self.liquidity_gate = liquidity_gate or LiquidityGateAgent()

    async def evaluate(self, ticker: str, *, macro: MacroSnapshot | None = None) -> BridgeResult:
        spec = apply_env_defaults(parse_instrument_token(ticker))
        apply_spec_to_env(spec)
        analysis_sym = analysis_ticker(spec)
        macro_ctx = macro or await get_macro_context()
        consensus = await self.consensus.analyze(analysis_sym, macro=macro_ctx)

        if consensus.consensus_score < self.config.min_consensus_score:
            return BridgeResult(
                intent=None,
                consensus=consensus,
                macro=macro_ctx,
                knn_scale=0.0,
                liquidity_paused=False,
                skipped_reason=f"consensus {consensus.consensus_score:.2f} below {self.config.min_consensus_score}",
            )

        if macro_ctx.regime in self.config.blocked_regimes:
            return BridgeResult(
                intent=None,
                consensus=consensus,
                macro=macro_ctx,
                knn_scale=0.0,
                liquidity_paused=False,
                skipped_reason=f"macro regime {macro_ctx.regime} blocks directional entry",
            )

        if consensus.consensus_recommendation in (
            Recommendation.SELL,
            Recommendation.STRONG_SELL,
            Recommendation.HOLD,
        ):
            return BridgeResult(
                intent=None,
                consensus=consensus,
                macro=macro_ctx,
                knn_scale=0.0,
                liquidity_paused=False,
                skipped_reason=f"consensus {consensus.consensus_recommendation.value}",
            )

        liquidity_paused = False
        if self.config.require_liquidity_clear:
            if not self.liquidity_gate.execution_allowed(analysis_sym):
                liquidity_paused = True
                return BridgeResult(
                    intent=None,
                    consensus=consensus,
                    macro=macro_ctx,
                    knn_scale=0.0,
                    liquidity_paused=True,
                    skipped_reason=f"liquidity gate: {self.liquidity_gate.pause_reason(analysis_sym)}",
                )

        knn_scale = await knn_position_scale(analysis_sym)
        qty = max(1.0, self.config.base_quantity * knn_scale * min(1.0, consensus.consensus_score))

        intent = TradeIntent(
            instrument=to_instrument_id(spec),
            side=OrderSide.BUY,
            quantity=qty,
            order_type=OrderType.MARKET,
            rationale=(
                f"consensus={consensus.consensus_score:.2f} "
                f"agreement={consensus.agreement_pct:.0%} regime={macro_ctx.regime} "
                f"knn_scale={knn_scale:.2f}"
            ),
            strategy_name="consensus_bridge",
        )
        return BridgeResult(
            intent=intent,
            consensus=consensus,
            macro=macro_ctx,
            knn_scale=knn_scale,
            liquidity_paused=liquidity_paused,
        )

    def generate_intent(self, ticker: str | None = None) -> TradeIntent:
        """Sync entry point for TradingWorkflow SignalProvider protocol."""
        sym = ticker or os.environ.get("GTP_SIGNAL_TICKER", "AAPL")
        result = run_coro(self.evaluate(sym))
        ensure_event_loop()
        if result.intent is None:
            raise RuntimeError(result.skipped_reason or "bridge produced no intent")
        return result.intent

    def generate_demo_intent(self, ticker: str = "AAPL") -> TradeIntent:
        return self.generate_intent(ticker)


class ConsensusSignalProvider:
    """SignalProvider adapter for global_trading TradingWorkflow."""

    def __init__(self, bridge: ConsensusSignalBridge, ticker: str = "AAPL") -> None:
        self.bridge = bridge
        self.ticker = ticker

    def generate_demo_intent(self) -> TradeIntent:
        return self.bridge.generate_demo_intent(self.ticker)
