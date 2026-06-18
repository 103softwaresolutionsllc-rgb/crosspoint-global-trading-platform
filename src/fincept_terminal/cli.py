#!/usr/bin/env python3
"""
Fincept Terminal CLI - Main entry point for the financial intelligence platform
"""

import argparse
import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from fincept_terminal.analytics.dcf import DCFModel
from fincept_terminal.analytics.portfolio import PortfolioOptimizer
from fincept_terminal.analytics.risk import RiskMetrics
from fincept_terminal.agents.value_investors.buffett import BuffettAgent
from fincept_terminal.agents.value_investors.graham import GrahamAgent
from fincept_terminal.agents.value_investors.lynch import LynchAgent
from fincept_terminal.agents.value_investors.dunlap import IanDunlapAgent
from fincept_terminal.agents.quant_agents.simons import SimonsAgent
from fincept_terminal.connectors.yahoo_finance import YahooFinanceConnector
from fincept_terminal.connectors.fred import FREDConnector
from fincept_terminal.connectors.kraken import KrakenConnector

_FINCEPT_BLUE = "#0066CC"
_FINCEPT_DARK = "#0B1020"

console = Console()

@dataclass
class CLIConfig:
    """Configuration for CLI operations"""
    verbose: bool = False
    config_file: Path = Path("config/fincept.yaml")
    output_format: str = "table"  # table, json, csv


def print_banner(console: Console) -> None:
    """Print Fincept Terminal banner"""
    title = Text("FINCEPT TERMINAL", style=f"bold {_FINCEPT_BLUE}")
    subtitle = Text("State-of-the-art financial intelligence platform", style="bold #A9B4C4")
    
    panel_content = Text()
    panel_content.append_text(title)
    panel_content.append("\n")
    panel_content.append_text(subtitle)
    panel_content.append("\n\n")
    panel_content.append("Version: 4.0.2", style="dim #A9B4C4")
    panel_content.append("\n")
    panel_content.append("© 2025-2026 Fincept Corporation", style="dim #A9B4C4")
    
    panel = Panel(
        panel_content,
        border_style=_FINCEPT_BLUE,
        padding=(1, 2)
    )
    console.print(panel)


async def run_dcf_analysis(ticker: str, config: CLIConfig) -> None:
    """Run DCF analysis for a given ticker"""
    console.print(f"[bold green]Running DCF Analysis for {ticker}[/bold green]")
    
    try:
        dcf = DCFModel()
        result = await dcf.analyze(ticker)
        
        console.print(Panel(
            f"DCF Valuation: ${result.valuation:,.2f}\n"
            f"Fair Value: ${result.fair_value:,.2f}\n"
            f"Upside: {result.upside:.1%}%",
            title=f"{ticker} DCF Analysis",
            border_style="green"
        ))
    except Exception as e:
        console.print(f"[bold red]Error in DCF analysis: {e}[/bold red]")


async def run_portfolio_optimization(config: CLIConfig) -> None:
    """Run portfolio optimization"""
    console.print("[bold green]Running Portfolio Optimization[/bold green]")
    
    try:
        optimizer = PortfolioOptimizer()
        result = await optimizer.optimize()
        
        console.print(Panel(
            f"Expected Return: {result.expected_return:.2%}\n"
            f"Annual Volatility: {result.volatility:.2%}\n"
            f"Sharpe Ratio: {result.sharpe_ratio:.2f}\n"
            f"Max Drawdown: {result.max_drawdown:.2%}",
            title="Portfolio Optimization Results",
            border_style="green"
        ))
    except Exception as e:
        console.print(f"[bold red]Error in portfolio optimization: {e}[/bold red]")


async def run_risk_analysis(config: CLIConfig) -> None:
    """Run risk analysis"""
    console.print("[bold green]Running Risk Analysis[/bold green]")
    
    try:
        risk = RiskMetrics()
        result = await risk.calculate_metrics()
        
        console.print(Panel(
            f"Value at Risk (95%): {result.var_95:.2%}\n"
            f"Value at Risk (99%): {result.var_99:.2%}\n"
            f"Conditional VaR: {result.cvar:.2%}\n"
            f"Beta: {result.beta:.2f}",
            title="Risk Metrics",
            border_style="green"
        ))
    except Exception as e:
        console.print(f"[bold red]Error in risk analysis: {e}[/bold red]")


async def run_agent_analysis(agent_name: str, ticker: str, config: CLIConfig) -> None:
    """Run AI agent analysis"""
    console.print(f"[bold green]Running {agent_name} Agent Analysis[/bold green]")
    
    try:
        if agent_name.lower() == "buffett":
            agent = BuffettAgent()
        elif agent_name.lower() == "graham":
            agent = GrahamAgent()
        elif agent_name.lower() == "lynch":
            agent = LynchAgent()
        elif agent_name.lower() == "dunlap":
            agent = IanDunlapAgent()
        elif agent_name.lower() == "simons":
            agent = SimonsAgent()
        else:
            console.print(f"[bold red]Unknown agent: {agent_name}[/bold red]")
            return
        
        result = await agent.analyze(ticker)
        
        console.print(Panel(
            f"Recommendation: {result.recommendation}\n"
            f"Confidence: {result.confidence:.1%}\n"
            f"Reasoning: {result.reasoning}",
            title=f"{agent_name.title()} Analysis for {ticker}",
            border_style="blue"
        ))
    except Exception as e:
        console.print(f"[bold red]Error in agent analysis: {e}[/bold red]")


async def run_data_retrieval(source: str, symbol: str, config: CLIConfig) -> None:
    """Run data retrieval from various sources"""
    console.print(f"[bold green]Retrieving data from {source} for {symbol}[/bold green]")
    
    try:
        if source.lower() == "yahoo":
            connector = YahooFinanceConnector()
        elif source.lower() == "fred":
            connector = FREDConnector()
        elif source.lower() == "kraken":
            connector = KrakenConnector()
        else:
            console.print(f"[bold red]Unknown data source: {source}[/bold red]")
            return
        
        data = await connector.get_data(symbol)
        
        console.print(Panel(
            f"Data Points Retrieved: {len(data)}\n"
            f"Latest Value: {data.iloc[-1].iloc[-1]:.2f}\n"
            f"Date Range: {data.index[0]} to {data.index[-1]}",
            title=f"{source.title()} Data for {symbol}",
            border_style="cyan"
        ))
    except Exception as e:
        console.print(f"[bold red]Error in data retrieval: {e}[/bold red]")


async def run_macro(config: CLIConfig, force_refresh: bool = False) -> None:
    """Fetch and display FRED macro snapshot used by agents."""
    from fincept_terminal.agents.macro_context import get_macro_context

    console.print("[bold green]FRED Macro Snapshot[/bold green]")
    try:
        snap = await get_macro_context(force_refresh=force_refresh)
        lines = [
            f"Regime: {snap.regime}",
            f"GDP growth (YoY): {snap.gdp_growth_yoy:+.2f}%",
            f"CPI (YoY): {snap.cpi_yoy:.2f}%",
            f"Unemployment: {snap.unemployment:.2f}%",
            f"Fed funds: {snap.fed_funds_rate:.2f}%",
            f"10Y-2Y spread: {snap.yield_curve_10y2y:+.2f}%",
            f"Source: {snap.source}",
            f"Pill: {snap.pill_text()}",
        ]
        console.print(Panel("\n".join(lines), title="Macro Context (Phase 3)", border_style="cyan"))
    except Exception as e:
        console.print(f"[bold red]Error loading macro: {e}[/bold red]")


async def run_consensus(ticker: str, config: CLIConfig) -> None:
    """Run four-agent consensus analysis on a single ticker."""
    from fincept_terminal.agents.orchestration.consensus import AgentConsensus

    console.print(f"[bold green]Running Agent Consensus for {ticker}[/bold green]")
    try:
        result = await AgentConsensus().analyze(ticker)
        lines = [
            f"Consensus Score: {result.consensus_score:.2f}",
            f"Recommendation: {result.consensus_recommendation.value}",
            f"Agreement: {result.agreement_pct:.0%}",
        ]
        for ar in result.agent_results:
            macro = (ar.additional_data or {}).get("macro", {})
            regime = macro.get("regime", "n/a")
            lines.append(f"  {ar.agent_name}: {ar.recommendation.value} ({ar.confidence:.0%}) · macro:{regime}")
        console.print(Panel("\n".join(lines), title=f"Consensus — {ticker}", border_style="blue"))
    except Exception as e:
        console.print(f"[bold red]Error in consensus analysis: {e}[/bold red]")


async def run_screen(watchlist: str, min_consensus: float, config: CLIConfig) -> None:
    """Screen a watchlist through the agent consensus pipeline."""
    from fincept_terminal.agents.orchestration.screener import AgentScreener

    tickers = [t.strip().upper() for t in watchlist.split(",") if t.strip()]
    console.print(f"[bold green]Screening {len(tickers)} tickers (min score {min_consensus})[/bold green]")
    try:
        result = await AgentScreener(min_consensus_score=min_consensus).screen(tickers)
        lines = [f"Passed: {len(result.passed)} / {len(tickers)} ({result.pass_rate:.0%})"]
        for r in result.passed:
            lines.append(f"  {r.ticker}: {r.consensus_score:.2f} ({r.consensus_recommendation.value})")
        if result.failed:
            lines.append(f"Failed: {', '.join(result.failed)}")
        console.print(Panel("\n".join(lines), title="Watchlist Screen", border_style="green"))
    except Exception as e:
        console.print(f"[bold red]Error in screening: {e}[/bold red]")


async def run_backtest(ticker: str, strategy: str, start: str, end: str, config: CLIConfig) -> None:
    """Run historical backtest simulation."""
    from global_trading.backtest.engine import BacktestConfig, BacktestEngine

    console.print(f"[bold green]Backtesting {ticker} ({strategy})[/bold green]")
    try:
        engine = BacktestEngine(
            BacktestConfig(ticker=ticker, start=start, end=end)
        )
        result = engine.run(strategy=strategy)
        console.print(Panel(
            f"Total Return: {result.total_return:.2%}\n"
            f"Sharpe Ratio: {result.sharpe_ratio:.2f}\n"
            f"Max Drawdown: {result.max_drawdown:.2%}\n"
            f"Win Rate: {result.win_rate:.0%}\n"
            f"Trades: {result.num_trades}\n"
            f"Final Equity: ${result.final_equity:,.2f}",
            title=f"Backtest — {ticker}",
            border_style="green",
        ))
    except Exception as e:
        console.print(f"[bold red]Error in backtest: {e}[/bold red]")


async def run_workflow(workflow_path: Path, config: CLIConfig) -> None:
    """Execute a JSON workflow definition."""
    from fincept_terminal.workflows.executor import WorkflowExecutor
    from fincept_terminal.workflows.schema import WorkflowDefinition

    console.print(f"[bold green]Running workflow: {workflow_path}[/bold green]")
    try:
        definition = WorkflowDefinition.from_json(workflow_path)
        result = await WorkflowExecutor().run(definition)
        status = "SUCCESS" if result.success else "FAILED"
        console.print(Panel(
            f"Status: {status}\n"
            f"Nodes executed: {len(result.node_outputs)}\n"
            f"Errors: {result.errors or 'none'}",
            title=definition.name,
            border_style="green" if result.success else "red",
        ))
    except Exception as e:
        console.print(f"[bold red]Error running workflow: {e}[/bold red]")


def create_parser() -> argparse.ArgumentParser:
    """Create the main argument parser"""
    parser = argparse.ArgumentParser(
        prog="fincept",
        description="Fincept Terminal - Financial Intelligence Platform"
    )
    
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument("--config", "-c", type=Path, help="Configuration file path")
    parser.add_argument("--output", "-o", choices=["table", "json", "csv"], default="table",
                       help="Output format")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Analytics commands
    dcf_parser = subparsers.add_parser("dcf", help="Run DCF analysis")
    dcf_parser.add_argument("--ticker", "-t", required=True, help="Stock ticker symbol")
    
    portfolio_parser = subparsers.add_parser("portfolio-optimize", help="Run portfolio optimization")
    
    risk_parser = subparsers.add_parser("risk-analysis", help="Run risk analysis")
    
    # Agent commands
    agent_parser = subparsers.add_parser("agent", help="Run AI agent analysis")
    agent_parser.add_argument("--buffett", action="store_true", help="Use Buffett agent")
    agent_parser.add_argument("--graham", action="store_true", help="Use Graham agent")
    agent_parser.add_argument("--lynch", action="store_true", help="Use Lynch agent")
    agent_parser.add_argument("--dunlap", action="store_true", help="Use Dunlap agent")
    agent_parser.add_argument("--simons", action="store_true", help="Use Simons agent")
    agent_parser.add_argument("--ticker", "-t", required=True, help="Stock ticker symbol")
    
    # Data commands
    data_parser = subparsers.add_parser("data", help="Retrieve market data")
    data_parser.add_argument("--source", "-s", choices=["yahoo", "fred", "kraken"], 
                           required=True, help="Data source")
    data_parser.add_argument("--ticker", "-t", help="Stock ticker symbol")
    data_parser.add_argument("--series", help="FRED series code")
    data_parser.add_argument("--pair", help="Crypto trading pair (e.g., BTC/USD)")
    
    macro_parser = subparsers.add_parser("macro", help="Show FRED macro snapshot (Phase 3)")
    macro_parser.add_argument("--refresh", action="store_true", help="Force refresh macro cache")

    consensus_parser = subparsers.add_parser("consensus", help="Run four-agent consensus on a ticker")
    consensus_parser.add_argument("--ticker", "-t", required=True, help="Stock ticker symbol")

    screen_parser = subparsers.add_parser("screen", help="Screen watchlist with agent consensus")
    screen_parser.add_argument("--watchlist", "-w", required=True, help="Comma-separated tickers")
    screen_parser.add_argument("--min-consensus", type=float, default=0.5, help="Minimum consensus score")

    backtest_parser = subparsers.add_parser("backtest", help="Run historical backtest")
    backtest_parser.add_argument("--ticker", "-t", required=True, help="Stock ticker symbol")
    backtest_parser.add_argument("--strategy", default="buy_hold", help="Strategy name")
    backtest_parser.add_argument("--start", default="2020-01-01", help="Start date YYYY-MM-DD")
    backtest_parser.add_argument("--end", default="2024-12-31", help="End date YYYY-MM-DD")

    workflow_parser = subparsers.add_parser("workflow", help="Execute a JSON workflow pipeline")
    workflow_parser.add_argument("--file", "-f", type=Path, required=True, help="Workflow JSON path")

    # Legacy commands for compatibility
    subparsers.add_parser("run-once", help="Run trading workflow once")
    subparsers.add_parser("reconcile", help="Reconcile positions")
    subparsers.add_parser("crypto-once", help="Run crypto trading once")
    subparsers.add_parser("metrics", help="Show trading metrics")
    
    return parser


async def main() -> None:
    """Main CLI entry point"""
    parser = create_parser()
    args = parser.parse_args()
    
    config = CLIConfig(
        verbose=args.verbose,
        config_file=args.config or Path("config/fincept.yaml"),
        output_format=args.output
    )
    
    if not args.verbose and args.command not in ["metrics"]:
        print_banner(console)
    
    if args.command == "dcf":
        await run_dcf_analysis(args.ticker, config)
    elif args.command == "portfolio-optimize":
        await run_portfolio_optimization(config)
    elif args.command == "risk-analysis":
        await run_risk_analysis(config)
    elif args.command == "agent":
        if args.buffett:
            await run_agent_analysis("buffett", args.ticker, config)
        elif args.graham:
            await run_agent_analysis("graham", args.ticker, config)
        elif args.lynch:
            await run_agent_analysis("lynch", args.ticker, config)
        elif args.dunlap:
            await run_agent_analysis("dunlap", args.ticker, config)
        elif args.simons:
            await run_agent_analysis("simons", args.ticker, config)
        else:
            console.print("[bold red]Please specify an agent (--buffett, --graham, --lynch, --dunlap, or --simons)[/bold red]")
    elif args.command == "data":
        symbol = args.ticker or args.series or args.pair
        if not symbol:
            console.print("[bold red]Please specify --ticker, --series, or --pair[/bold red]")
            return
        await run_data_retrieval(args.source, symbol, config)
    elif args.command == "macro":
        await run_macro(config, force_refresh=args.refresh)
    elif args.command == "consensus":
        await run_consensus(args.ticker, config)
    elif args.command == "screen":
        await run_screen(args.watchlist, args.min_consensus, config)
    elif args.command == "backtest":
        await run_backtest(args.ticker, args.strategy, args.start, args.end, config)
    elif args.command == "workflow":
        await run_workflow(args.file, config)
    elif args.command in ["run-once", "reconcile", "crypto-once", "metrics"]:
        console.print("[bold yellow]Legacy commands - migrating to Fincept Terminal architecture[/bold yellow]")
        # Import and run legacy functionality
        from global_trading.cli import main as legacy_main
        sys.argv = ["gtp", args.command]
        legacy_main()
    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
