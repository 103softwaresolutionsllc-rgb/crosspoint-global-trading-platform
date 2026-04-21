"""
Warren Buffett Agent
Based on Warren Buffett's value investing principles:
- Circle of competence
- Economic moats
- Management quality
- Margin of safety
- Long-term perspective
"""

import asyncio
from typing import Dict, Any
import numpy as np

from ..base import BaseAgent, AgentResult, AgentType, Recommendation


class BuffettAgent(BaseAgent):
    """
    Warren Buffett AI Agent implementing his investment philosophy:
    
    Core Principles:
    1. Circle of Competence: Only invest in businesses you understand
    2. Economic Moats: Look for sustainable competitive advantages
    3. Management Quality: Trustworthy, competent management
    4. Financial Strength: Strong balance sheets and consistent earnings
    5. Margin of Safety: Buy at discount to intrinsic value
    6. Long-term Hold: "Our favorite holding period is forever"
    """
    
    def __init__(self):
        super().__init__("Warren Buffett", AgentType.VALUE_INVESTOR)
        
        # Buffett's key criteria thresholds
        self.thresholds = {
            'roe': (0.15, 1.0),  # ROE > 15%
            'debt_to_equity': (0, 0.5),  # Debt/Equity < 0.5
            'profit_margin': (0.10, 1.0),  # Profit margin > 10%
            'pe_ratio': (5, 20),  # P/E between 5-20
            'pb_ratio': (0.5, 3.0),  # P/B between 0.5-3.0
            'current_ratio': (1.5, 10.0),  # Current ratio > 1.5
            'operating_margin': (0.15, 1.0),  # Operating margin > 15%
            'revenue_growth': (-0.05, 0.25),  # Moderate growth
        }
        
    async def analyze(self, ticker: str, **kwargs) -> AgentResult:
        """Analyze stock using Warren Buffett's principles"""
        try:
            # Get financial data
            financial_data = await self._get_financial_data(ticker)
            
            # Calculate Buffett-specific metrics
            buffett_metrics = await self._calculate_buffett_metrics(financial_data)
            
            # Assess economic moat
            moat_score = await self._assess_economic_moat(ticker, financial_data)
            
            # Evaluate management quality
            management_score = await self._evaluate_management(financial_data)
            
            # Calculate intrinsic value
            intrinsic_value = await self._calculate_intrinsic_value(financial_data)
            
            # Determine margin of safety
            margin_of_safety = self._calculate_margin_of_safety(
                intrinsic_value, financial_data['current_price']
            )
            
            # Get overall confidence
            confidence = self._calculate_buffett_confidence(
                buffett_metrics, moat_score, management_score, margin_of_safety
            )
            
            # Generate recommendation
            recommendation = self._get_buffett_recommendation(confidence, margin_of_safety)
            
            # Create reasoning
            reasoning = await self._generate_buffett_reasoning(
                ticker, buffett_metrics, moat_score, management_score, 
                margin_of_safety, intrinsic_value
            )
            
            # Identify risk factors and catalysts
            risk_factors = await self._identify_buffett_risks(financial_data, buffett_metrics)
            catalysts = await self._identify_buffett_catalysts(financial_data, buffett_metrics)
            
            return AgentResult(
                agent_name=self.name,
                ticker=ticker.upper(),
                recommendation=recommendation,
                confidence=confidence,
                reasoning=reasoning,
                key_metrics={
                    **buffett_metrics,
                    'moat_score': moat_score,
                    'management_score': management_score,
                    'intrinsic_value': intrinsic_value,
                    'margin_of_safety': margin_of_safety,
                },
                risk_factors=risk_factors,
                catalysts=catalysts,
                price_target=intrinsic_value,
                time_horizon="5+ years",
                additional_data={
                    'investment_style': 'Value Investing',
                    'holding_period': 'Long-term',
                    'risk_tolerance': 'Low to Medium',
                }
            )
            
        except Exception as e:
            return AgentResult(
                agent_name=self.name,
                ticker=ticker.upper(),
                recommendation=Recommendation.HOLD,
                confidence=0.0,
                reasoning=f"Analysis failed: {str(e)}",
                key_metrics={},
                risk_factors=["Analysis error"],
                catalysts=[]
            )
    
    async def _calculate_buffett_metrics(self, financial_data: Dict[str, Any]) -> Dict[str, float]:
        """Calculate Buffett-specific financial metrics"""
        info = financial_data.get('info', {})
        financials = financial_data.get('financials', {})
        balance_sheet = financial_data.get('balance_sheet', {})
        
        metrics = {
            'roe': info.get('returnOnEquity', 0),
            'roa': info.get('returnOnAssets', 0),
            'debt_to_equity': info.get('debtToEquity', 0),
            'profit_margin': info.get('profitMargins', 0),
            'operating_margin': info.get('operatingMargins', 0),
            'pe_ratio': info.get('trailingPE', 0),
            'pb_ratio': info.get('priceToBook', 0),
            'dividend_yield': info.get('dividendYield', 0),
            'beta': info.get('beta', 1.0),
        }
        
        # Calculate additional Buffett metrics
        try:
            # Current ratio (liquidity)
            if not balance_sheet.empty:
                current_assets = balance_sheet.loc['Total Current Assets'].iloc[0] if 'Total Current Assets' in balance_sheet.index else 0
                current_liabilities = balance_sheet.loc['Total Current Liabilities'].iloc[0] if 'Total Current Liabilities' in balance_sheet.index else 1
                metrics['current_ratio'] = current_assets / current_liabilities if current_liabilities > 0 else 0
            else:
                metrics['current_ratio'] = 0
            
            # Revenue growth (5-year average)
            if not financials.empty and len(financials.columns) >= 5:
                revenues = [financials.loc['Total Revenue'].iloc[i] for i in range(min(5, len(financials.columns)))]
                if len(revenues) >= 2:
                    revenue_growth = (revenues[0] - revenues[-1]) / revenues[-1] / len(revenues)
                    metrics['revenue_growth'] = revenue_growth
                else:
                    metrics['revenue_growth'] = 0
            else:
                metrics['revenue_growth'] = info.get('revenueGrowth', 0)
            
            # Owner earnings (Buffett's preferred metric)
            cash_flow = financial_data.get('cash_flow', {})
            if not cash_flow.empty:
                operating_cash = cash_flow.loc['Total Cash From Operating Activities'].iloc[0] if 'Total Cash From Operating Activities' in cash_flow.index else 0
                maintenance_capex = cash_flow.loc['Capital Expenditures'].iloc[0] if 'Capital Expenditures' in cash_flow.index else 0
                metrics['owner_earnings'] = operating_cash - maintenance_capex
            else:
                metrics['owner_earnings'] = 0
            
        except Exception:
            # Use defaults if calculations fail
            metrics.update({
                'current_ratio': 0,
                'revenue_growth': 0,
                'owner_earnings': 0,
            })
        
        return metrics
    
    async def _assess_economic_moat(self, ticker: str, financial_data: Dict[str, Any]) -> float:
        """Assess the strength of economic moat (0-1 scale)"""
        moat_factors = []
        
        info = financial_data.get('info', {})
        
        # High and stable ROE suggests moat
        roe = info.get('returnOnEquity', 0)
        if roe > 0.20:
            moat_factors.append(0.8)
        elif roe > 0.15:
            moat_factors.append(0.6)
        elif roe > 0.10:
            moat_factors.append(0.4)
        else:
            moat_factors.append(0.1)
        
        # Low debt suggests strong position
        debt_to_equity = info.get('debtToEquity', 1.0)
        if debt_to_equity < 0.3:
            moat_factors.append(0.7)
        elif debt_to_equity < 0.5:
            moat_factors.append(0.5)
        elif debt_to_equity < 1.0:
            moat_factors.append(0.3)
        else:
            moat_factors.append(0.1)
        
        # High profit margins suggest pricing power
        profit_margin = info.get('profitMargins', 0)
        if profit_margin > 0.20:
            moat_factors.append(0.8)
        elif profit_margin > 0.15:
            moat_factors.append(0.6)
        elif profit_margin > 0.10:
            moat_factors.append(0.4)
        else:
            moat_factors.append(0.1)
        
        # Consistent earnings (simplified check)
        net_income = info.get('netIncomeToCommon', 0)
        if net_income > 0:
            moat_factors.append(0.6)
        else:
            moat_factors.append(0.2)
        
        # Market leadership (simplified by market cap)
        market_cap = info.get('marketCap', 0)
        if market_cap > 100e9:  # > $100B
            moat_factors.append(0.7)
        elif market_cap > 10e9:  # > $10B
            moat_factors.append(0.5)
        elif market_cap > 1e9:  # > $1B
            moat_factors.append(0.3)
        else:
            moat_factors.append(0.1)
        
        return np.mean(moat_factors)
    
    async def _evaluate_management(self, financial_data: Dict[str, Any]) -> float:
        """Evaluate management quality (0-1 scale)"""
        management_factors = []
        
        info = financial_data.get('info', {})
        
        # Capital allocation (ROE)
        roe = info.get('returnOnEquity', 0)
        if roe > 0.20:
            management_factors.append(0.8)
        elif roe > 0.15:
            management_factors.append(0.6)
        elif roe > 0.10:
            management_factors.append(0.4)
        else:
            management_factors.append(0.1)
        
        # Operational efficiency (ROA)
        roa = info.get('returnOnAssets', 0)
        if roa > 0.10:
            management_factors.append(0.7)
        elif roa > 0.05:
            management_factors.append(0.5)
        elif roa > 0.02:
            management_factors.append(0.3)
        else:
            management_factors.append(0.1)
        
        # Financial prudence (debt levels)
        debt_to_equity = info.get('debtToEquity', 1.0)
        if debt_to_equity < 0.3:
            management_factors.append(0.8)
        elif debt_to_equity < 0.5:
            management_factors.append(0.6)
        elif debt_to_equity < 1.0:
            management_factors.append(0.4)
        else:
            management_factors.append(0.1)
        
        # Profitability management
        operating_margin = info.get('operatingMargins', 0)
        if operating_margin > 0.25:
            management_factors.append(0.8)
        elif operating_margin > 0.15:
            management_factors.append(0.6)
        elif operating_margin > 0.10:
            management_factors.append(0.4)
        else:
            management_factors.append(0.1)
        
        return np.mean(management_factors)
    
    async def _calculate_intrinsic_value(self, financial_data: Dict[str, Any]) -> float:
        """Calculate intrinsic value using Buffett's DCF approach"""
        try:
            info = financial_data.get('info', {})
            
            # Get key metrics
            current_eps = info.get('trailingEps', 0)
            book_value = info.get('bookValue', 0)
            current_price = info.get('currentPrice', 0)
            
            # Method 1: Graham Number (conservative)
            graham_number = np.sqrt(22.5 * current_eps * book_value) if current_eps > 0 and book_value > 0 else 0
            
            # Method 2: Owner earnings multiple
            cash_flow = financial_data.get('cash_flow', {})
            if not cash_flow.empty:
                operating_cash = cash_flow.loc['Total Cash From Operating Activities'].iloc[0] if 'Total Cash From Operating Activities' in cash_flow.index else 0
                maintenance_capex = cash_flow.loc['Capital Expenditures'].iloc[0] if 'Capital Expenditures' in cash_flow.index else 0
                owner_earnings = operating_cash - maintenance_capex
                
                shares_outstanding = info.get('sharesOutstanding', 1)
                owner_earnings_per_share = owner_earnings / shares_outstanding if shares_outstanding > 0 else 0
                
                # Buffett typically pays 8-15x owner earnings
                owner_earnings_value = owner_earnings_per_share * 12  # Midpoint of 8-15x
            else:
                owner_earnings_value = 0
            
            # Method 3: Conservative P/E multiple (Buffett avoids high P/E)
            pe_value = current_eps * 15 if current_eps > 0 else 0
            
            # Method 4: Asset-based valuation (floor value)
            asset_value = book_value * 1.5 if book_value > 0 else 0
            
            # Combine methods with weights
            intrinsic_values = [v for v in [graham_number, owner_earnings_value, pe_value, asset_value] if v > 0]
            
            if intrinsic_values:
                # Use median to avoid outliers
                intrinsic_value = np.median(intrinsic_values)
            else:
                intrinsic_value = current_price  # Fallback to current price
            
            return intrinsic_value
            
        except Exception:
            return financial_data.get('current_price', 0)
    
    def _calculate_margin_of_safety(self, intrinsic_value: float, current_price: float) -> float:
        """Calculate margin of safety percentage"""
        if current_price <= 0:
            return 0.0
        
        margin = (intrinsic_value - current_price) / current_price
        return max(margin, 0.0)  # Only positive margin of safety
    
    def _calculate_buffett_confidence(self, metrics: Dict[str, float], 
                                    moat_score: float, management_score: float,
                                    margin_of_safety: float) -> float:
        """Calculate overall confidence score"""
        # Financial metrics confidence
        financial_confidence = self._calculate_confidence(metrics, self.thresholds)
        
        # Weight different factors according to Buffett's priorities
        weights = {
            'financial': 0.3,
            'moat': 0.25,
            'management': 0.25,
            'margin_of_safety': 0.2
        }
        
        # Normalize margin of safety to 0-1 scale (Buffett wants at least 25%)
        margin_score = min(margin_of_safety / 0.25, 1.0)
        
        overall_confidence = (
            weights['financial'] * financial_confidence +
            weights['moat'] * moat_score +
            weights['management'] * management_score +
            weights['margin_of_safety'] * margin_score
        )
        
        return overall_confidence
    
    def _get_buffett_recommendation(self, confidence: float, margin_of_safety: float) -> Recommendation:
        """Get recommendation based on Buffett's criteria"""
        # Buffett needs both good quality AND margin of safety
        if confidence >= 0.7 and margin_of_safety >= 0.25:
            return Recommendation.STRONG_BUY
        elif confidence >= 0.6 and margin_of_safety >= 0.15:
            return Recommendation.BUY
        elif confidence >= 0.5 and margin_of_safety >= 0.10:
            return Recommendation.HOLD
        elif margin_of_safety < 0 or confidence < 0.3:
            return Recommendation.SELL
        else:
            return Recommendation.HOLD
    
    async def _generate_buffett_reasoning(self, ticker: str, metrics: Dict[str, float],
                                       moat_score: float, management_score: float,
                                       margin_of_safety: float, intrinsic_value: float) -> str:
        """Generate Buffett-style reasoning"""
        reasoning_parts = []
        
        # Business quality assessment
        if moat_score > 0.7:
            reasoning_parts.append(f"{ticker} demonstrates a strong economic moat with sustainable competitive advantages.")
        elif moat_score > 0.5:
            reasoning_parts.append(f"{ticker} shows moderate competitive positioning.")
        else:
            reasoning_parts.append(f"{ticker} lacks a clear economic moat.")
        
        # Management assessment
        if management_score > 0.7:
            reasoning_parts.append("Management demonstrates excellent capital allocation and operational efficiency.")
        elif management_score > 0.5:
            reasoning_parts.append("Management appears competent but there's room for improvement.")
        else:
            reasoning_parts.append("Management quality raises concerns.")
        
        # Financial strength
        roe = metrics.get('roe', 0)
        if roe > 0.20:
            reasoning_parts.append(f"Exceptional ROE of {roe:.1%} indicates strong profitability.")
        elif roe > 0.15:
            reasoning_parts.append(f"Solid ROE of {roe:.1%} demonstrates good returns on equity.")
        
        # Margin of safety
        if margin_of_safety >= 0.25:
            reasoning_parts.append(f"Significant margin of safety of {margin_of_safety:.1%} provides downside protection.")
        elif margin_of_safety >= 0.15:
            reasoning_parts.append(f"Moderate margin of safety of {margin_of_safety:.1%}.")
        elif margin_of_safety < 0:
            reasoning_parts.append("Stock appears overvalued with negative margin of safety.")
        
        # Valuation
        current_price = metrics.get('current_price', 0)
        if intrinsic_value > 0 and current_price > 0:
            reasoning_parts.append(f"Intrinsic value estimated at ${intrinsic_value:.2f} vs current price of ${current_price:.2f}.")
        
        # Conclusion
        if margin_of_safety >= 0.25 and moat_score > 0.6:
            reasoning_parts.append("This aligns with our principle of buying wonderful businesses at fair prices.")
        elif margin_of_safety < 0:
            reasoning_parts.append("We prefer to wait for a better price rather than overpay.")
        
        return " ".join(reasoning_parts)
    
    async def _identify_buffett_risks(self, financial_data: Dict[str, Any], 
                                    metrics: Dict[str, float]) -> list:
        """Identify Buffett-specific risk factors"""
        risks = []
        
        # High valuation risk
        pe_ratio = metrics.get('pe_ratio', 0)
        if pe_ratio > 30:
            risks.append("High P/E ratio suggests overvaluation")
        elif pe_ratio > 25:
            risks.append("Elevated P/E ratio limits margin of safety")
        
        # Weak economic moat
        if metrics.get('moat_score', 0) < 0.4:
            risks.append("Lacks sustainable competitive advantages")
        
        # Poor management
        if metrics.get('management_score', 0) < 0.4:
            risks.append("Management quality concerns")
        
        # High debt
        debt_to_equity = metrics.get('debt_to_equity', 0)
        if debt_to_equity > 1.0:
            risks.append("Excessive debt burdens the business")
        
        # Low profitability
        roe = metrics.get('roe', 0)
        if roe < 0.10:
            risks.append("Low return on equity indicates poor profitability")
        
        # Negative earnings
        eps = metrics.get('eps', 0)
        if eps < 0:
            risks.append("Negative earnings - business is losing money")
        
        # High volatility (Buffett prefers stable businesses)
        beta = metrics.get('beta', 1.0)
        if beta > 1.5:
            risks.append("High beta indicates excessive volatility")
        
        return risks
    
    async def _identify_buffett_catalysts(self, financial_data: Dict[str, Any], 
                                        metrics: Dict[str, float]) -> list:
        """Identify Buffett-specific positive catalysts"""
        catalysts = []
        
        # Strong profitability
        roe = metrics.get('roe', 0)
        if roe > 0.20:
            catalysts.append("Exceptional return on equity")
        elif roe > 0.15:
            catalysts.append("Strong return on equity")
        
        # Strong moat
        if metrics.get('moat_score', 0) > 0.7:
            catalysts.append("Wide economic moat provides competitive protection")
        
        # Conservative balance sheet
        debt_to_equity = metrics.get('debt_to_equity', 0)
        if debt_to_equity < 0.3:
            catalysts.append("Conservative debt levels provide financial flexibility")
        
        # Consistent earnings growth
        revenue_growth = metrics.get('revenue_growth', 0)
        if revenue_growth > 0.10:
            catalysts.append("Steady revenue growth")
        
        # Shareholder-friendly policies
        dividend_yield = metrics.get('dividend_yield', 0)
        if dividend_yield > 0.02:
            catalysts.append("Regular dividend payments to shareholders")
        
        # Attractive valuation
        margin_of_safety = metrics.get('margin_of_safety', 0)
        if margin_of_safety > 0.30:
            catalysts.append("Significant margin of safety")
        elif margin_of_safety > 0.20:
            catalysts.append("Adequate margin of safety")
        
        return catalysts
