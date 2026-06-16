"""
Ian Dunlap Agent
Inspired by Ian Dunlap's emphasis on owning elite market leaders with:
- Durable competitive moats
- Strong free cash flow and margins
- Category leadership
- Secular growth trends
- Buy-and-hold compounders
- Quality over speculation
"""

import asyncio
from typing import Dict, Any
import numpy as np

from ..base import BaseAgent, AgentResult, AgentType, Recommendation
from ..macro_context import apply_macro_to_result, resolve_macro


class IanDunlapAgent(BaseAgent):
    """
    Ian Dunlap-inspired AI Agent focused on elite compounders.

    Core Principles:
    1. Buy dominant category leaders
    2. Favor businesses with durable moats
    3. Prioritize free cash flow, margins, and execution
    4. Focus on secular winners, not mediocre businesses
    5. Hold quality companies for long periods
    6. Avoid weak balance sheets and low-conviction names
    7. Concentrate on businesses with repeatable compounding potential
    """

    def __init__(self):
        super().__init__("Ian Dunlap", AgentType.GROWTH_INVESTOR)

        self.thresholds = {
            "revenue_growth": (0.08, 0.60),
            "earnings_growth": (0.10, 0.60),
            "operating_margin": (0.15, 1.0),
            "profit_margin": (0.10, 1.0),
            "roe": (0.15, 1.0),
            "debt_to_equity": (0.0, 0.8),
            "free_cash_flow_margin": (0.08, 1.0),
            "current_ratio": (1.0, 5.0),
        }

    async def analyze(self, ticker: str, **kwargs) -> AgentResult:
        """Analyze a stock using an Ian Dunlap-inspired quality growth framework."""
        try:
            macro = await resolve_macro(kwargs)
            financial_data = await self._get_financial_data(ticker)

            quality_metrics = await self._calculate_quality_metrics(financial_data)
            moat_score = await self._assess_moat(financial_data, quality_metrics)
            leadership_score = await self._assess_category_leadership(financial_data, quality_metrics)
            cash_flow_score = self._assess_cash_flow_quality(quality_metrics)
            compounder_score = self._calculate_compounder_score(
                quality_metrics,
                moat_score,
                leadership_score,
                cash_flow_score,
            )
            intrinsic_value = await self._calculate_intrinsic_value(financial_data, quality_metrics)

            confidence = self._calculate_dunlap_confidence(
                quality_metrics,
                moat_score,
                leadership_score,
                cash_flow_score,
                compounder_score,
            )
            recommendation = self._get_dunlap_recommendation(
                confidence,
                compounder_score,
                moat_score,
            )

            reasoning = await self._generate_reasoning(
                ticker,
                quality_metrics,
                moat_score,
                leadership_score,
                cash_flow_score,
                compounder_score,
                intrinsic_value,
            )

            risk_factors = await self._identify_risks(
                quality_metrics,
                moat_score,
                leadership_score,
                cash_flow_score,
            )
            catalysts = await self._identify_catalysts(
                quality_metrics,
                moat_score,
                leadership_score,
                cash_flow_score,
                compounder_score,
            )

            result = AgentResult(
                agent_name=self.name,
                ticker=ticker.upper(),
                recommendation=recommendation,
                confidence=confidence,
                reasoning=reasoning,
                key_metrics={
                    **quality_metrics,
                    "moat_score": moat_score,
                    "leadership_score": leadership_score,
                    "cash_flow_score": cash_flow_score,
                    "compounder_score": compounder_score,
                    "intrinsic_value": intrinsic_value,
                },
                risk_factors=risk_factors,
                catalysts=catalysts,
                price_target=intrinsic_value,
                time_horizon="3-10 years",
                additional_data={
                    "investment_style": "Quality Growth / Compounders",
                    "philosophy": "Own elite businesses, not average stocks",
                    "portfolio_bias": "Market leaders with durable moats",
                },
            )
            return apply_macro_to_result(result, macro, "dunlap")

        except Exception as e:
            return AgentResult(
                agent_name=self.name,
                ticker=ticker.upper(),
                recommendation=Recommendation.HOLD,
                confidence=0.0,
                reasoning=f"Analysis failed: {str(e)}",
                key_metrics={},
                risk_factors=["Analysis error"],
                catalysts=[],
            )

    async def _calculate_quality_metrics(self, financial_data: Dict[str, Any]) -> Dict[str, float]:
        """Calculate quality and compounding metrics."""
        info = financial_data.get("info", {})
        financials = financial_data.get("financials", {})
        balance_sheet = financial_data.get("balance_sheet", {})
        cashflow = financial_data.get("cashflow", {})

        metrics = {
            "current_price": info.get("currentPrice", 0),
            "market_cap": info.get("marketCap", 0),
            "pe_ratio": info.get("trailingPE", 0),
            "forward_pe": info.get("forwardPE", 0),
            "peg_ratio": info.get("pegRatio", 0),
            "price_to_sales": info.get("priceToSalesTrailing12Months", 0),
            "gross_margin": info.get("grossMargins", 0),
            "operating_margin": info.get("operatingMargins", 0),
            "profit_margin": info.get("profitMargins", 0),
            "roe": info.get("returnOnEquity", 0),
            "roa": info.get("returnOnAssets", 0),
            "revenue_growth": info.get("revenueGrowth", 0),
            "earnings_growth": info.get("earningsGrowth", 0),
            "debt_to_equity": info.get("debtToEquity", 0),
            "current_ratio": info.get("currentRatio", 0),
            "eps": info.get("trailingEps", 0),
            "free_cash_flow": info.get("freeCashflow", 0),
            "operating_cash_flow": info.get("operatingCashflow", 0),
            "revenue": info.get("totalRevenue", 0),
            "shares_outstanding": info.get("sharesOutstanding", 0),
        }

        revenue = metrics["revenue"]
        free_cash_flow = metrics["free_cash_flow"]
        operating_cash_flow = metrics["operating_cash_flow"]

        metrics["free_cash_flow_margin"] = (free_cash_flow / revenue) if revenue > 0 else 0
        metrics["cash_conversion"] = (free_cash_flow / operating_cash_flow) if operating_cash_flow > 0 else 0

        try:
            if hasattr(financials, "empty") and not financials.empty and len(financials.columns) >= 3:
                revenues = []
                for i in range(min(3, len(financials.columns))):
                    if "Total Revenue" in financials.index:
                        revenues.append(financials.loc["Total Revenue"].iloc[i])
                if len(revenues) >= 2 and revenues[-1] > 0:
                    periods = len(revenues) - 1
                    metrics["revenue_cagr"] = (revenues[0] / revenues[-1]) ** (1 / periods) - 1
                else:
                    metrics["revenue_cagr"] = metrics["revenue_growth"]
            else:
                metrics["revenue_cagr"] = metrics["revenue_growth"]

            if hasattr(cashflow, "empty") and not cashflow.empty and len(cashflow.columns) >= 3:
                fcf_series = []
                row_name = None
                for candidate in ["Free Cash Flow", "FreeCashFlow"]:
                    if candidate in cashflow.index:
                        row_name = candidate
                        break
                if row_name:
                    for i in range(min(3, len(cashflow.columns))):
                        fcf_series.append(cashflow.loc[row_name].iloc[i])
                consistent_fcf = len(fcf_series) >= 2 and all(v > 0 for v in fcf_series)
                metrics["consistent_free_cash_flow"] = 1.0 if consistent_fcf else 0.0
            else:
                metrics["consistent_free_cash_flow"] = 1.0 if free_cash_flow > 0 else 0.0

            if hasattr(balance_sheet, "empty") and not balance_sheet.empty:
                cash = 0
                debt = 0
                for cash_key in ["Cash And Cash Equivalents", "Cash", "Cash And Short Term Investments"]:
                    if cash_key in balance_sheet.index:
                        cash = balance_sheet.loc[cash_key].iloc[0]
                        break
                for debt_key in ["Total Debt", "Long Term Debt", "Total Liabilities Net Minority Interest"]:
                    if debt_key in balance_sheet.index:
                        debt = balance_sheet.loc[debt_key].iloc[0]
                        break
                metrics["net_cash_ratio"] = (cash - debt) / metrics["market_cap"] if metrics["market_cap"] > 0 else 0
            else:
                metrics["net_cash_ratio"] = 0

        except Exception:
            metrics.setdefault("revenue_cagr", metrics["revenue_growth"])
            metrics.setdefault("consistent_free_cash_flow", 1.0 if free_cash_flow > 0 else 0.0)
            metrics.setdefault("net_cash_ratio", 0)

        return metrics

    async def _assess_moat(
        self,
        financial_data: Dict[str, Any],
        metrics: Dict[str, float],
    ) -> float:
        """Estimate moat strength on a 0-1 scale."""
        info = financial_data.get("info", {})
        sector = info.get("sector", "").lower()
        industry = info.get("industry", "").lower()

        factors = []

        gross_margin = metrics.get("gross_margin", 0)
        if gross_margin >= 0.60:
            factors.append(0.9)
        elif gross_margin >= 0.45:
            factors.append(0.7)
        elif gross_margin >= 0.30:
            factors.append(0.5)
        else:
            factors.append(0.2)

        operating_margin = metrics.get("operating_margin", 0)
        if operating_margin >= 0.25:
            factors.append(0.9)
        elif operating_margin >= 0.18:
            factors.append(0.7)
        elif operating_margin >= 0.10:
            factors.append(0.5)
        else:
            factors.append(0.2)

        if metrics.get("roe", 0) >= 0.20:
            factors.append(0.8)
        elif metrics.get("roe", 0) >= 0.15:
            factors.append(0.6)
        else:
            factors.append(0.3)

        moat_friendly_industries = [
            "software",
            "semiconductor",
            "internet content",
            "payments",
            "medical devices",
            "consumer electronics",
        ]
        if any(name in industry for name in moat_friendly_industries):
            factors.append(0.8)
        elif sector in {"technology", "healthcare", "communication services"}:
            factors.append(0.6)
        else:
            factors.append(0.4)

        return float(np.mean(factors))

    async def _assess_category_leadership(
        self,
        financial_data: Dict[str, Any],
        metrics: Dict[str, float],
    ) -> float:
        """Estimate whether the business looks like a category leader."""
        info = financial_data.get("info", {})
        sector = info.get("sector", "").lower()
        market_cap = metrics.get("market_cap", 0)

        factors = []

        if market_cap >= 200e9:
            factors.append(0.9)
        elif market_cap >= 50e9:
            factors.append(0.75)
        elif market_cap >= 10e9:
            factors.append(0.55)
        else:
            factors.append(0.3)

        revenue_growth = metrics.get("revenue_cagr", 0)
        if revenue_growth >= 0.20:
            factors.append(0.8)
        elif revenue_growth >= 0.12:
            factors.append(0.6)
        elif revenue_growth >= 0.08:
            factors.append(0.4)
        else:
            factors.append(0.2)

        if metrics.get("free_cash_flow_margin", 0) >= 0.15:
            factors.append(0.8)
        elif metrics.get("free_cash_flow_margin", 0) >= 0.08:
            factors.append(0.6)
        else:
            factors.append(0.3)

        leadership_sectors = {"technology", "healthcare", "communication services", "consumer defensive"}
        factors.append(0.7 if sector in leadership_sectors else 0.5)

        return float(np.mean(factors))

    def _assess_cash_flow_quality(self, metrics: Dict[str, float]) -> float:
        """Score cash generation quality on a 0-1 scale."""
        factors = []

        fcf_margin = metrics.get("free_cash_flow_margin", 0)
        if fcf_margin >= 0.20:
            factors.append(1.0)
        elif fcf_margin >= 0.12:
            factors.append(0.8)
        elif fcf_margin >= 0.08:
            factors.append(0.6)
        elif fcf_margin > 0:
            factors.append(0.4)
        else:
            factors.append(0.1)

        conversion = metrics.get("cash_conversion", 0)
        if conversion >= 0.80:
            factors.append(0.9)
        elif conversion >= 0.60:
            factors.append(0.7)
        elif conversion >= 0.40:
            factors.append(0.5)
        else:
            factors.append(0.2)

        factors.append(metrics.get("consistent_free_cash_flow", 0))

        net_cash_ratio = metrics.get("net_cash_ratio", 0)
        if net_cash_ratio >= 0.05:
            factors.append(0.8)
        elif net_cash_ratio >= 0:
            factors.append(0.6)
        else:
            factors.append(0.3)

        return float(np.mean(factors))

    def _calculate_compounder_score(
        self,
        metrics: Dict[str, float],
        moat_score: float,
        leadership_score: float,
        cash_flow_score: float,
    ) -> float:
        """Blend growth, margins, moat, and cash flow into one compounder score."""
        growth_score = 0.0
        revenue_cagr = metrics.get("revenue_cagr", 0)
        earnings_growth = metrics.get("earnings_growth", 0)

        if revenue_cagr >= 0.20:
            growth_score += 0.5
        elif revenue_cagr >= 0.12:
            growth_score += 0.35
        elif revenue_cagr >= 0.08:
            growth_score += 0.2

        if earnings_growth >= 0.20:
            growth_score += 0.5
        elif earnings_growth >= 0.12:
            growth_score += 0.35
        elif earnings_growth >= 0.08:
            growth_score += 0.2

        valuation_score = 0.2
        peg_ratio = metrics.get("peg_ratio", 0)
        forward_pe = metrics.get("forward_pe", 0)
        if 0 < peg_ratio <= 1.5:
            valuation_score = 0.8
        elif 0 < peg_ratio <= 2.0:
            valuation_score = 0.6
        elif forward_pe and forward_pe <= 25:
            valuation_score = 0.55
        elif forward_pe and forward_pe <= 35:
            valuation_score = 0.4

        return float(
            0.25 * growth_score +
            0.25 * moat_score +
            0.20 * leadership_score +
            0.15 * cash_flow_score +
            0.10 * valuation_score
        )

    async def _calculate_intrinsic_value(
        self,
        financial_data: Dict[str, Any],
        metrics: Dict[str, float],
    ) -> float:
        """Estimate fair value using quality-growth oriented methods."""
        current_price = metrics.get("current_price", 0)
        eps = metrics.get("eps", 0)
        revenue = metrics.get("revenue", 0)
        shares = metrics.get("shares_outstanding", 0)
        fcf = metrics.get("free_cash_flow", 0)

        values = []

        if eps > 0:
            growth = max(metrics.get("earnings_growth", 0), 0.08)
            fair_pe = min(max(growth * 100, 18), 32)
            values.append(eps * fair_pe)

        if revenue > 0 and shares > 0:
            revenue_per_share = revenue / shares
            sales_multiple = 6 if metrics.get("operating_margin", 0) >= 0.20 else 4
            values.append(revenue_per_share * sales_multiple)

        if fcf > 0 and shares > 0:
            fcf_per_share = fcf / shares
            fcf_multiple = 28 if metrics.get("free_cash_flow_margin", 0) >= 0.15 else 22
            values.append(fcf_per_share * fcf_multiple)

        if values:
            return float(np.mean(values))
        return current_price

    def _calculate_dunlap_confidence(
        self,
        metrics: Dict[str, float],
        moat_score: float,
        leadership_score: float,
        cash_flow_score: float,
        compounder_score: float,
    ) -> float:
        """Calculate overall conviction."""
        financial_confidence = self._calculate_confidence(metrics, self.thresholds)
        return float(
            0.25 * financial_confidence +
            0.20 * moat_score +
            0.20 * leadership_score +
            0.15 * cash_flow_score +
            0.20 * compounder_score
        )

    def _get_dunlap_recommendation(
        self,
        confidence: float,
        compounder_score: float,
        moat_score: float,
    ) -> Recommendation:
        """Translate conviction into a recommendation."""
        if confidence >= 0.75 and compounder_score >= 0.70 and moat_score >= 0.70:
            return Recommendation.STRONG_BUY
        if confidence >= 0.62 and compounder_score >= 0.58:
            return Recommendation.BUY
        if confidence >= 0.48:
            return Recommendation.HOLD
        if confidence < 0.30 or moat_score < 0.30:
            return Recommendation.SELL
        return Recommendation.HOLD

    async def _generate_reasoning(
        self,
        ticker: str,
        metrics: Dict[str, float],
        moat_score: float,
        leadership_score: float,
        cash_flow_score: float,
        compounder_score: float,
        intrinsic_value: float,
    ) -> str:
        """Generate a concise quality-growth thesis."""
        parts = []

        if moat_score >= 0.75:
            parts.append(f"{ticker} appears to have a strong competitive moat supported by superior margins and returns.")
        elif moat_score >= 0.55:
            parts.append(f"{ticker} shows signs of a respectable moat, though not an elite one.")
        else:
            parts.append(f"{ticker} does not yet show clear moat strength.")

        if leadership_score >= 0.75:
            parts.append("The business looks like a category leader with scale advantages.")
        elif leadership_score >= 0.55:
            parts.append("The company appears competitively relevant in its category.")
        else:
            parts.append("Category leadership is not clearly established.")

        if cash_flow_score >= 0.75:
            parts.append("Cash flow quality is strong, which supports long-term compounding.")
        elif cash_flow_score >= 0.55:
            parts.append("Cash generation is acceptable but not top-tier.")
        else:
            parts.append("Cash flow quality is a concern.")

        revenue_cagr = metrics.get("revenue_cagr", 0)
        earnings_growth = metrics.get("earnings_growth", 0)
        if revenue_cagr >= 0.15:
            parts.append(f"Revenue growth of {revenue_cagr:.1%} supports the growth thesis.")
        if earnings_growth >= 0.15:
            parts.append(f"Earnings growth of {earnings_growth:.1%} reinforces operating momentum.")

        if 0 < metrics.get("peg_ratio", 0) <= 1.5:
            parts.append(f"PEG ratio of {metrics['peg_ratio']:.2f} suggests valuation is still reasonable for a quality.")
        elif metrics.get("forward_pe", 0) > 35:
            parts.append(f"Forward P/E of {metrics['forward_pe']:.2f} signals a premium valuation.")

        current_price = metrics.get("current_price", 0)
        if intrinsic_value > 0 and current_price > 0:
            parts.append(f"Estimated fair value is ${intrinsic_value:.2f} versus a current price of ${current_price:.2f}.")

        if compounder_score >= 0.70:
            parts.append("Overall, this fits the profile of a high-quality long-term compounder.")
        elif compounder_score >= 0.55:
            parts.append("Overall, this is a decent quality-growth candidate but not a top-tier setup.")
        else:
            parts.append("Overall, this falls short of an elite compounder profile.")

        return " ".join(parts)

    async def _identify_risks(
        self,
        metrics: Dict[str, float],
        moat_score: float,
        leadership_score: float,
        cash_flow_score: float,
    ) -> list:
        """Identify major risks."""
        risks = []

        if moat_score < 0.45:
            risks.append("Competitive moat appears limited")
        if leadership_score < 0.45:
            risks.append("Category leadership is unclear")
        if cash_flow_score < 0.50:
            risks.append("Cash flow quality is below preferred standards")
        if metrics.get("debt_to_equity", 0) > 1.0:
            risks.append("Leverage is elevated")
        if metrics.get("operating_margin", 0) < 0.10:
            risks.append("Operating margins are too thin for an elite-quality profile")
        if metrics.get("free_cash_flow_margin", 0) < 0.05:
            risks.append("Free cash flow margin is weak")
        if metrics.get("revenue_cagr", 0) < 0.08:
            risks.append("Top-line growth is too slow for a premium growth thesis")
        if metrics.get("forward_pe", 0) > 40:
            risks.append("Valuation leaves little room for execution misses")

        return risks

    async def _identify_catalysts(
        self,
        metrics: Dict[str, float],
        moat_score: float,
        leadership_score: float,
        cash_flow_score: float,
        compounder_score: float,
    ) -> list:
        """Identify positive catalysts."""
        catalysts = []

        if moat_score >= 0.75:
            catalysts.append("Strong moat characteristics")
        if leadership_score >= 0.70:
            catalysts.append("Category leadership and scale advantages")
        if cash_flow_score >= 0.75:
            catalysts.append("Excellent free cash flow quality")
        if metrics.get("revenue_cagr", 0) >= 0.15:
            catalysts.append("Sustained double-digit revenue growth")
        if metrics.get("earnings_growth", 0) >= 0.18:
            catalysts.append("Strong earnings expansion")
        if metrics.get("operating_margin", 0) >= 0.20:
            catalysts.append("High operating margins")
        if 0 < metrics.get("peg_ratio", 0) <= 1.5:
            catalysts.append("Reasonable valuation relative to growth")
        if compounder_score >= 0.70:
            catalysts.append("Elite long-term compounding profile")

        return catalysts
