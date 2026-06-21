"""
Ray Dalio Macro Agent
Based on Ray Dalio's macro investing and economic machine principles:
- Economic machine cycles (growth/inflation quadrants)
- Debt cycle vulnerability (leverage, interest coverage)
- Risk parity suitability (beta, volatility)
- Multiples compression adjusting to interest rates (Fed Funds)
"""

import asyncio
from typing import Dict, Any, List
import numpy as np
import pandas as pd

from ..base import BaseAgent, AgentResult, AgentType, Recommendation
from ..macro_context import apply_macro_to_result, resolve_macro


class DalioAgent(BaseAgent):
    """
    Ray Dalio AI Agent implementing macroeconomic cycle and debt dynamics analysis.

    Core Principles:
    1. The Economic Machine: Track growth and inflation quadrants.
    2. Debt Cycles: Check sensitivity to interest rates and debt expansion limits.
    3. Risk Parity: Assess asset suitability for risk-balanced portfolio contribution.
    4. Capital Preservation: Ensure strong balance sheet health in tightening/recessionary cycles.
    """

    def __init__(self):
        super().__init__("Ray Dalio", AgentType.MACRO_AGENT)

        # Dalio's specific thresholds
        self.thresholds = {
            "debt_to_equity": (0.0, 0.6),        # Prefers low to moderate leverage
            "current_ratio": (1.2, 5.0),         # Healthy liquidity
            "operating_margin": (0.10, 1.0),      # Stable margins
            "beta": (0.4, 1.2),                  # Balanced market sensitivity
            "dividend_yield": (0.015, 0.08),     # Steady dividend returns
        }

    async def analyze(self, ticker: str, **kwargs) -> AgentResult:
        """Analyze a stock using Ray Dalio's macro and debt cycle principles."""
        try:
            macro = await resolve_macro(kwargs)
            financial_data = await self._get_financial_data(ticker)

            info = financial_data.get("info", {})
            sector = info.get("sector", "")
            industry = info.get("industry", "")
            price_data = financial_data.get("price_data")

            # Calculate Dalio-specific metrics
            dalio_metrics = await self._calculate_dalio_metrics(financial_data)

            # Evaluate Economic Machine Regime Alignment (0-1 scale)
            regime_score = self._calculate_regime_alignment(
                sector, industry, dalio_metrics, macro.regime
            )

            # Assess Debt Cycle safety (0-1 scale)
            debt_score = self._assess_debt_cycle_safety(dalio_metrics, macro.regime)

            # Evaluate Risk Parity contribution potential (0-1 scale)
            risk_parity_score = self._assess_risk_parity_suitability(dalio_metrics, price_data)

            # Calculate intrinsic value adjusted for interest rate multiple drag
            intrinsic_value = await self._calculate_intrinsic_value(financial_data, macro.fed_funds_rate)

            # Calculate margin of safety
            margin_of_safety = self._calculate_margin_of_safety(
                intrinsic_value, financial_data.get("current_price", 0.0)
            )

            # Calculate overall confidence
            confidence = self._calculate_dalio_confidence(
                dalio_metrics, regime_score, debt_score, risk_parity_score, margin_of_safety
            )

            # Get recommendation
            recommendation = self._get_dalio_recommendation(confidence, regime_score, debt_score)

            # Generate reasoning
            reasoning = await self._generate_dalio_reasoning(
                ticker,
                dalio_metrics,
                regime_score,
                debt_score,
                risk_parity_score,
                margin_of_safety,
                intrinsic_value,
                macro.regime,
                sector,
            )

            # Identify risks and catalysts
            risk_factors = await self._identify_dalio_risks(dalio_metrics, regime_score, debt_score, macro.regime)
            catalysts = await self._identify_dalio_catalysts(dalio_metrics, regime_score, debt_score, margin_of_safety)

            result = AgentResult(
                agent_name=self.name,
                ticker=ticker.upper(),
                recommendation=recommendation,
                confidence=confidence,
                reasoning=reasoning,
                key_metrics={
                    **dalio_metrics,
                    "regime_alignment_score": regime_score,
                    "debt_safety_score": debt_score,
                    "risk_parity_score": risk_parity_score,
                    "intrinsic_value": intrinsic_value,
                    "margin_of_safety": margin_of_safety,
                },
                risk_factors=risk_factors,
                catalysts=catalysts,
                price_target=intrinsic_value,
                time_horizon="3-5 years",
                additional_data={
                    "investment_style": "Macro Systematic / Risk Parity",
                    "philosophy": "Understand the economic machine and credit cycles",
                    "portfolio_bias": "Diversified, risk-adjusted, macro-aligned assets",
                },
            )
            return apply_macro_to_result(result, macro, "dalio")

        except Exception as e:
            return AgentResult(
                agent_name=self.name,
                ticker=ticker.upper(),
                recommendation=Recommendation.HOLD,
                confidence=0.0,
                reasoning=f"Macro analysis failed: {str(e)}",
                key_metrics={},
                risk_factors=["Analysis error"],
                catalysts=[],
            )

    async def _calculate_dalio_metrics(self, financial_data: Dict[str, Any]) -> Dict[str, float]:
        """Calculate and normalize key financial indicators for Ray Dalio's checks."""
        info = financial_data.get("info", {})
        financials = financial_data.get("financials", {})

        # Normalize debt to equity to decimal format (handles percentage returned from yfinance)
        raw_de = info.get("debtToEquity", 0.0)
        debt_to_equity = raw_de / 100.0 if raw_de > 1.5 else raw_de

        metrics = {
            "current_price": info.get("currentPrice", 0.0),
            "debt_to_equity": debt_to_equity,
            "beta": info.get("beta", 1.0),
            "dividend_yield": info.get("dividendYield", 0.0),
            "current_ratio": info.get("currentRatio", 1.0),
            "operating_margin": info.get("operatingMargins", 0.0),
            "pe_ratio": info.get("trailingPE", 0.0),
        }

        # Interest coverage ratio calculation from financials
        interest_coverage = 5.0
        try:
            if financials is not None and not financials.empty:
                operating_income = 0.0
                interest_expense = 0.0
                for idx in financials.index:
                    idx_str = str(idx).lower()
                    if "operating income" in idx_str or "ebit" in idx_str:
                        operating_income = float(financials.loc[idx].iloc[0])
                    elif "interest expense" in idx_str:
                        interest_expense = abs(float(financials.loc[idx].iloc[0]))
                if interest_expense > 0:
                    interest_coverage = operating_income / interest_expense
        except Exception:
            pass

        metrics["interest_coverage"] = interest_coverage

        # Margin stability calculation
        margin_stability = 1.0
        try:
            if financials is not None and not financials.empty and "Gross Profit" in financials.index and "Total Revenue" in financials.index:
                gross_profits = financials.loc["Gross Profit"]
                revenues = financials.loc["Total Revenue"]
                margins = (gross_profits / revenues).dropna()
                if len(margins) >= 2:
                    std_dev = float(margins.std())
                    margin_stability = max(0.0, 1.0 - std_dev)
        except Exception:
            pass

        metrics["margin_stability"] = margin_stability

        return metrics

    def _calculate_regime_alignment(self, sector: str, industry: str, metrics: dict, regime: str) -> float:
        """Assess how well the asset aligns with Ray Dalio's economic quadrant rules."""
        sec_lower = (sector or "").lower()

        # 1. Inflationary Regime
        if regime == "inflationary":
            if sec_lower in ["energy", "basic materials", "industrials"]:
                return 0.90
            if metrics.get("dividend_yield", 0) > 0.03:
                return 0.80
            if metrics.get("margin_stability", 1.0) > 0.90:  # pricing power
                return 0.75
            return 0.50

        # 2. Recession Risk or Late Cycle
        elif regime in ["recession_risk", "late_cycle"]:
            if sec_lower in ["consumer defensive", "utilities", "healthcare"]:
                return 0.90
            if metrics.get("debt_to_equity", 0) < 0.3 and metrics.get("current_ratio", 1.0) > 1.5:
                return 0.85
            if metrics.get("beta", 1.0) < 0.8:
                return 0.80
            return 0.40

        # 3. Expansion
        elif regime == "expansion":
            if sec_lower in ["technology", "consumer cyclical", "communication services"]:
                return 0.90
            if metrics.get("beta", 1.0) > 1.0:
                return 0.80
            return 0.60

        # 4. Mid Cycle / default
        else:
            if metrics.get("beta", 1.0) <= 1.1 and metrics.get("debt_to_equity", 0) <= 0.6:
                return 0.80
            return 0.65

    def _assess_debt_cycle_safety(self, metrics: dict, regime: str) -> float:
        """Assess asset vulnerability to debt cycles and credit contraction."""
        factors = []

        # Leverage
        de = metrics.get("debt_to_equity", 0.0)
        if de < 0.2:
            factors.append(0.95)
        elif de < 0.5:
            factors.append(0.80)
        elif de < 1.0:
            factors.append(0.50)
        else:
            factors.append(0.20)

        # Interest coverage
        ic = metrics.get("interest_coverage", 5.0)
        if ic > 10.0:
            factors.append(0.95)
        elif ic > 5.0:
            factors.append(0.80)
        elif ic > 2.0:
            factors.append(0.50)
        else:
            factors.append(0.10)

        # Liquidity
        cr = metrics.get("current_ratio", 1.0)
        if cr > 2.0:
            factors.append(0.90)
        elif cr > 1.2:
            factors.append(0.70)
        else:
            factors.append(0.30)

        score = float(np.mean(factors))
        if regime in ["recession_risk", "late_cycle"] and score < 0.6:
            score *= 0.8

        return score

    def _assess_parity_volatility(self, price_data: pd.DataFrame) -> float:
        """Calculate annualized volatility from historical prices."""
        if price_data is not None and not price_data.empty:
            try:
                closes = price_data["Close"].dropna()
                if len(closes) >= 30:
                    returns = closes.pct_change().dropna()
                    vol = float(returns.std() * np.sqrt(252))
                    return vol
            except Exception:
                pass
        return 0.25  # default baseline volatility

    def _assess_risk_parity_suitability(self, metrics: dict, price_data: pd.DataFrame) -> float:
        """Assess suitability for a risk-balanced asset allocation."""
        factors = []

        # Beta (optimal contribution around 0.5 - 1.0)
        beta = metrics.get("beta", 1.0)
        if 0.5 <= beta <= 1.0:
            factors.append(0.95)
        elif 0.3 <= beta < 0.5 or 1.0 < beta <= 1.3:
            factors.append(0.75)
        else:
            factors.append(0.40)

        # Volatility check
        vol = self._assess_parity_volatility(price_data)
        if vol < 0.20:
            factors.append(0.95)
        elif vol < 0.35:
            factors.append(0.75)
        else:
            factors.append(0.45)

        return float(np.mean(factors))

    async def _calculate_intrinsic_value(self, financial_data: Dict[str, Any], fed_funds_rate: float) -> float:
        """Calculate intrinsic value adjusting multiples based on interest rates (Fed Funds)."""
        info = financial_data.get("info", {})
        current_price = info.get("currentPrice", 0.0)
        eps = info.get("trailingEps", 0.0)
        book_value = info.get("bookValue", 0.0)

        # Interest rate multiple drag
        rate = fed_funds_rate if fed_funds_rate > 0 else 3.0
        interest_rate_drag = max(0.5, 1.0 - (rate - 3.0) * 0.05)

        base_pe = 16.0 * interest_rate_drag
        base_pb = 2.0 * interest_rate_drag

        values = []

        # P/E Valuation
        if eps > 0:
            values.append(eps * base_pe)

        # P/B Valuation
        if book_value > 0:
            values.append(book_value * base_pb)

        # Owner earnings multiple (adjusted)
        cash_flow = financial_data.get("cash_flow", {})
        if not cash_flow.empty:
            try:
                operating_cash = cash_flow.loc["Total Cash From Operating Activities"].iloc[0] if "Total Cash From Operating Activities" in cash_flow.index else 0
                maintenance_capex = cash_flow.loc["Capital Expenditures"].iloc[0] if "Capital Expenditures" in cash_flow.index else 0
                owner_earnings = operating_cash - maintenance_capex
                shares_outstanding = info.get("sharesOutstanding", 1)
                owner_earnings_per_share = owner_earnings / shares_outstanding if shares_outstanding > 0 else 0
                if owner_earnings_per_share > 0:
                    values.append(owner_earnings_per_share * (12.0 * interest_rate_drag))
            except Exception:
                pass

        if values:
            return float(np.mean(values))
        return current_price

    def _calculate_margin_of_safety(self, intrinsic_value: float, current_price: float) -> float:
        """Calculate percentage difference between intrinsic value and current price."""
        if current_price <= 0:
            return 0.0
        margin = (intrinsic_value - current_price) / current_price
        return float(max(margin, -1.0))

    def _calculate_dalio_confidence(
        self,
        metrics: dict,
        regime_score: float,
        debt_score: float,
        risk_parity_score: float,
        margin_of_safety: float,
    ) -> float:
        """Calculate overall confidence score."""
        financial_confidence = self._calculate_confidence(metrics, self.thresholds)

        weights = {
            "financial": 0.20,
            "regime": 0.30,
            "debt_cycle": 0.25,
            "risk_parity": 0.15,
            "margin_of_safety": 0.10,
        }

        margin_score = min(max(margin_of_safety / 0.20, 0.0), 1.0)

        overall_confidence = (
            weights["financial"] * financial_confidence +
            weights["regime"] * regime_score +
            weights["debt_cycle"] * debt_score +
            weights["risk_parity"] * risk_parity_score +
            weights["margin_of_safety"] * margin_score
        )
        return float(np.clip(overall_confidence, 0.0, 1.0))

    def _get_dalio_recommendation(self, confidence: float, regime_score: float, debt_score: float) -> Recommendation:
        """Translate Dalio-specific criteria to Recommendation enum."""
        if confidence >= 0.72 and regime_score >= 0.70 and debt_score >= 0.70:
            return Recommendation.STRONG_BUY
        elif confidence >= 0.60 and regime_score >= 0.55:
            return Recommendation.BUY
        elif confidence >= 0.40:
            return Recommendation.HOLD
        elif debt_score < 0.40 or confidence < 0.25:
            return Recommendation.SELL
        else:
            return Recommendation.HOLD

    async def _generate_dalio_reasoning(
        self,
        ticker: str,
        metrics: dict,
        regime_score: float,
        debt_score: float,
        risk_parity_score: float,
        margin_of_safety: float,
        intrinsic_value: float,
        regime: str,
        sector: str,
    ) -> str:
        """Generate Ray Dalio macro analysis rationale."""
        parts = []

        parts.append(f"{ticker} (Sector: {sector or 'N/A'}) analyzed under Dalio's economic machine framework.")
        parts.append(f"Regime alignment score is {regime_score:.1%} for the current '{regime}' environment.")

        if debt_score >= 0.75:
            parts.append(f"Strong balance sheet characteristics (debt safety score: {debt_score:.1%}) indicate high resilience to credit contraction cycles.")
        elif debt_score >= 0.50:
            parts.append(f"Moderate balance sheet risk (debt safety score: {debt_score:.1%}).")
        else:
            parts.append(f"Vulnerable balance sheet structure (debt safety score: {debt_score:.1%}) presents significant tail risk under high rates or credit contractions.")

        if risk_parity_score >= 0.80:
            parts.append(f"Excellent risk parity suitability (score: {risk_parity_score:.1%}) with a balanced beta of {metrics.get('beta', 1.0):.2f}.")
        else:
            parts.append(f"Higher volatility contribution (risk parity suitability: {risk_parity_score:.1%}).")

        current_price = metrics.get("current_price", 0.0)
        parts.append(f"Adjusted intrinsic value (interest rate drag applied) estimated at ${intrinsic_value:.2f} vs current price of ${current_price:.2f}.")

        if margin_of_safety > 0:
            parts.append(f"Margin of safety is {margin_of_safety:.1%}.")
        else:
            parts.append("Negative margin of safety.")

        return " ".join(parts)

    async def _identify_dalio_risks(self, metrics: dict, regime_score: float, debt_score: float, regime: str) -> List[str]:
        """Identify key risks based on macro and debt cycles."""
        risks = []
        if debt_score < 0.50:
            risks.append("Vulnerable debt/credit profile for rate tightening cycles")
        if metrics.get("debt_to_equity", 0.0) > 0.8:
            risks.append("Elevated debt-to-equity ratio increases solvency risk")
        if metrics.get("interest_coverage", 5.0) < 2.5:
            risks.append("Low interest coverage restricts operating breathing room")
        if regime_score < 0.50:
            risks.append(f"Mismatched with macro regime '{regime}'")
        if metrics.get("beta", 1.0) > 1.3:
            risks.append("High beta profile introduces excessive variance to a risk parity model")
        return risks

    async def _identify_dalio_catalysts(self, metrics: dict, regime_score: float, debt_score: float, margin_of_safety: float) -> List[str]:
        """Identify positive catalysts/supports under Ray Dalio principles."""
        catalysts = []
        if regime_score >= 0.75:
            catalysts.append("Strong tailwinds from current macroeconomic regime alignment")
        if debt_score >= 0.80:
            catalysts.append("Defensive balance sheet provides strategic resilience")
        if margin_of_safety >= 0.15:
            catalysts.append("Favorable margin of safety protects downside risk")
        if metrics.get("dividend_yield", 0.0) >= 0.025:
            catalysts.append("Robust dividend yield supports cash generation in flat markets")
        return catalysts
