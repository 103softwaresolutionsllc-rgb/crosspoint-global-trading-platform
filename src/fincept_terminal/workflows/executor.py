"""
Execute workflow DAGs — maps node types to agents, connectors, and analytics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from fincept_terminal.workflows.schema import WorkflowDefinition, WorkflowNode


@dataclass
class WorkflowRunResult:
    workflow_name: str
    node_outputs: dict[str, Any] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)
    success: bool = True


class WorkflowExecutor:
    """Run a WorkflowDefinition by executing nodes in topological order."""

    def _macro_from_context(self, context: dict[str, Any]) -> Any:
        """Pick macro snapshot from the most recent data/fred or macro node output."""
        for val in reversed(list(context.values())):
            if isinstance(val, dict) and "macro" in val:
                return val["macro"]
        return None

    async def run(self, workflow: WorkflowDefinition) -> WorkflowRunResult:
        result = WorkflowRunResult(workflow_name=workflow.name)
        context: dict[str, Any] = {}

        for node in workflow.topological_order():
            try:
                output = await self._execute_node(node, context)
                result.node_outputs[node.id] = output
                context[node.id] = output
            except Exception as e:
                result.errors[node.id] = str(e)
                result.success = False
                break

        return result

    async def _execute_node(self, node: WorkflowNode, context: dict[str, Any]) -> Any:
        node_type = node.type.lower()

        if node_type == "data/yahoo":
            return await self._run_yahoo(node)
        if node_type == "data/fred":
            return await self._run_fred(node)
        if node_type == "analytics/dcf":
            return await self._run_dcf(node, context)
        if node_type == "analytics/risk":
            return await self._run_risk(node)
        if node_type == "agent/consensus":
            return await self._run_consensus(node, context)
        if node_type.startswith("agent/"):
            return await self._run_agent(node, context)
        if node_type == "trading/risk_check":
            return self._run_risk_check(node, context)
        if node_type == "output/alert":
            return self._run_alert(node, context)
        if node_type == "output/report":
            return {"report": context}

        raise ValueError(f"Unknown node type: {node.type}")

    async def _run_yahoo(self, node: WorkflowNode) -> dict[str, Any]:
        from fincept_terminal.connectors.yahoo_finance import YahooFinanceConnector

        ticker = node.config.get("ticker", "SPY")
        connector = YahooFinanceConnector()
        data = await connector.get_data(ticker)
        return {"ticker": ticker, "rows": len(data), "latest_close": float(data["Close"].iloc[-1])}

    async def _run_fred(self, node: WorkflowNode) -> dict[str, Any]:
        from fincept_terminal.agents.macro_context import get_macro_context

        mode = node.config.get("mode", "macro_snapshot")
        if mode == "single_series":
            from fincept_terminal.connectors.fred import FREDConnector

            series = node.config.get("series", "GDP")
            async with FREDConnector() as connector:
                data = await connector.get_data(series)
            return {"series": series, "rows": len(data), "latest": float(data.iloc[-1].iloc[-1])}

        macro = await get_macro_context(force_refresh=node.config.get("force_refresh", False))
        return {"macro": macro.to_dict(), "regime": macro.regime, "pill": macro.pill_text()}

    async def _run_dcf(self, node: WorkflowNode, context: dict[str, Any]) -> dict[str, Any]:
        from fincept_terminal.analytics.dcf import DCFModel

        ticker = node.config.get("ticker")
        if not ticker:
            for val in context.values():
                if isinstance(val, dict) and "ticker" in val:
                    ticker = val["ticker"]
                    break
        ticker = ticker or "AAPL"
        dcf = DCFModel()
        result = await dcf.analyze(ticker)
        return {"ticker": ticker, "fair_value": result.fair_value, "upside": result.upside}

    async def _run_risk(self, node: WorkflowNode) -> dict[str, Any]:
        from fincept_terminal.analytics.risk import RiskMetrics

        risk = RiskMetrics()
        metrics = await risk.calculate_metrics()
        return {
            "var_95": metrics.var_95,
            "var_99": metrics.var_99,
            "sharpe": getattr(metrics, "sharpe_ratio", None),
        }

    async def _run_agent(self, node: WorkflowNode, context: dict[str, Any]) -> dict[str, Any]:
        agent_map = {
            "agent/buffett": "fincept_terminal.agents.value_investors.buffett.BuffettAgent",
            "agent/graham": "fincept_terminal.agents.value_investors.graham.GrahamAgent",
            "agent/lynch": "fincept_terminal.agents.value_investors.lynch.LynchAgent",
            "agent/dunlap": "fincept_terminal.agents.value_investors.dunlap.IanDunlapAgent",
        }
        import importlib

        ticker = node.config.get("ticker", "AAPL")
        class_path = agent_map.get(node.type.lower())
        if not class_path:
            raise ValueError(f"No agent mapping for {node.type}")
        module_path, class_name = class_path.rsplit(".", 1)
        cls = getattr(importlib.import_module(module_path), class_name)
        agent = cls()
        macro = self._macro_from_context(context)
        kwargs: dict[str, Any] = {"macro": macro} if macro else {}
        result = await agent.analyze(ticker, **kwargs)
        macro_data = (result.additional_data or {}).get("macro", {})
        return {
            "ticker": ticker,
            "agent": result.agent_name,
            "recommendation": result.recommendation.value,
            "confidence": result.confidence,
            "macro_regime": macro_data.get("regime"),
            "macro_pill": node.config.get("show_macro", True) and _macro_pill(macro_data),
        }

    async def _run_consensus(self, node: WorkflowNode, context: dict[str, Any]) -> dict[str, Any]:
        from fincept_terminal.agents.orchestration.consensus import AgentConsensus

        ticker = node.config.get("ticker", "AAPL")
        macro = self._macro_from_context(context)
        consensus = await AgentConsensus().analyze(ticker, macro=macro)
        return {
            "ticker": ticker,
            "consensus_score": consensus.consensus_score,
            "recommendation": consensus.consensus_recommendation.value,
            "agreement_pct": consensus.agreement_pct,
            "macro_regime": (consensus.agent_results[0].additional_data or {}).get("macro", {}).get("regime")
            if consensus.agent_results
            else None,
        }

    def _run_risk_check(self, node: WorkflowNode, context: dict[str, Any]) -> dict[str, Any]:
        from global_trading.core.risk import RiskConfig, RiskEngine

        engine = RiskEngine(RiskConfig(kill_switch=node.config.get("kill_switch", False)))
        engine.update_equity(node.config.get("equity", 100_000))
        return {"drawdown_pct": engine.current_drawdown_pct(), "allowed": True}

    def _run_alert(self, node: WorkflowNode, context: dict[str, Any]) -> dict[str, Any]:
        message = node.config.get("message", "Workflow completed")
        summary = {k: v for k, v in context.items() if isinstance(v, dict)}
        return {"alert": message, "summary": summary}


def _macro_pill(macro: dict) -> str | None:
    if not macro:
        return None
    gdp = macro.get("gdp_growth_yoy", 0)
    cpi = macro.get("cpi_yoy", 0)
    sign = "+" if gdp >= 0 else ""
    cpi_note = "cooling" if cpi < 3.0 else "elevated"
    return f"GDP {sign}{gdp:.1f}% · CPI {cpi_note}"
