"""
Benjamin Graham Agent
Based on Benjamin Graham's value investing principles:
- Margin of safety
- Net current asset value
- Earnings yield
- Dividend record
- Low debt levels
- Defensive vs Enterprising investor criteria
"""

import asyncio
from typing import Dict, Any
import numpy as np

from ..base import BaseAgent, AgentResult, AgentType, Recommendation
from ..macro_context import apply_macro_to_result, resolve_macro


class GrahamAgent(BaseAgent):
    """
    Benjamin Graham AI Agent implementing his value investing philosophy:
    
    Core Principles:
    1. Margin of Safety: Buy below intrinsic value
    2. Net-Net Analysis: Current assets exceed total liabilities
    3. Earnings Power: Consistent earnings history
    4. Financial Strength: Low debt and strong balance sheet
    5. Dividend Record: Long history of dividend payments
    6. Defensive vs Enterprising: Different criteria for investor types
    """
    
    def __init__(self):
        super().__init__("Benjamin Graham", AgentType.VALUE_INVESTOR)
        
        # Graham's defensive investor criteria
        self.defensive_criteria = {
            'pe_ratio': (0, 20),  # P/E ≤ 20
            'pb_ratio': (0, 1.5),  # P/B ≤ 1.5
            'debt_to_equity': (0, 0.5),  # Debt/Equity ≤ 0.5
            'current_ratio': (2.0, 10.0),  # Current ratio ≥ 2.0
            'dividend_yield': (0.02, 1.0),  # Dividend yield ≥ 2%
            'earnings_growth': (0, 0.30),  # Annual earnings growth ≤ 30%
        }
        
        # Graham's enterprising investor criteria (more flexible)
        self.enterprising_criteria = {
            'pe_ratio': (0, 15),  # P/E ≤ 15 (stricter)
            'pb_ratio': (0, 1.2),  # P/B ≤ 1.2 (stricter)
            'debt_to_equity': (0, 1.0),  # Debt/Equity ≤ 1.0 (more flexible)
            'current_ratio': (1.5, 10.0),  # Current ratio ≥ 1.5
            'tangible_book_value': (0, 1.0),  # Price ≤ Tangible book value
        }
        
    async def analyze(self, ticker: str, investor_type: str = "defensive", **kwargs) -> AgentResult:
        """Analyze stock using Benjamin Graham's principles"""
        try:
            macro = await resolve_macro(kwargs)
            # Get financial data
            financial_data = await self._get_financial_data(ticker)
            
            # Calculate Graham-specific metrics
            graham_metrics = await self._calculate_graham_metrics(financial_data)
            
            # Apply appropriate criteria
            if investor_type.lower() == "defensive":
                criteria = self.defensive_criteria
                analysis_type = "Defensive Investor"
            else:
                criteria = self.enterprising_criteria
                analysis_type = "Enterprising Investor"
            
            # Check Graham's key tests
            net_net_test = await self._net_net_test(financial_data)
            earnings_power_test = await self._earnings_power_test(financial_data)
            financial_strength_test = await self._financial_strength_test(financial_data)
            
            # Calculate intrinsic value using Graham's methods
            intrinsic_value_graham = await self._graham_number(financial_data)
            intrinsic_value_dcf = await self._graham_dcf(financial_data)
            intrinsic_value_net_net = await self._net_net_value(financial_data)
            
            # Choose most conservative intrinsic value
            intrinsic_values = [v for v in [intrinsic_value_graham, intrinsic_value_dcf, intrinsic_value_net_net] if v > 0]
            intrinsic_value = min(intrinsic_values) if intrinsic_values else financial_data['current_price']
            
            # Calculate margin of safety
            margin_of_safety = self._calculate_margin_of_safety(
                intrinsic_value, financial_data['current_price']
            )
            
            # Get overall confidence
            confidence = self._calculate_graham_confidence(
                graham_metrics, criteria, net_net_test, earnings_power_test, 
                financial_strength_test, margin_of_safety
            )
            
            # Generate recommendation
            recommendation = self._get_graham_recommendation(confidence, margin_of_safety, net_net_test)
            
            # Create reasoning
            reasoning = await self._generate_graham_reasoning(
                ticker, graham_metrics, criteria, net_net_test, 
                earnings_power_test, financial_strength_test, 
                margin_of_safety, intrinsic_value, analysis_type
            )
            
            # Identify risk factors and catalysts
            risk_factors = await self._identify_graham_risks(financial_data, graham_metrics)
            catalysts = await self._identify_graham_catalysts(financial_data, graham_metrics)
            
            result = AgentResult(
                agent_name=self.name,
                ticker=ticker.upper(),
                recommendation=recommendation,
                confidence=confidence,
                reasoning=reasoning,
                key_metrics={
                    **graham_metrics,
                    'net_net_test': net_net_test,
                    'earnings_power_test': earnings_power_test,
                    'financial_strength_test': financial_strength_test,
                    'intrinsic_value': intrinsic_value,
                    'margin_of_safety': margin_of_safety,
                    'graham_number': intrinsic_value_graham,
                    'net_net_value': intrinsic_value_net_net,
                },
                risk_factors=risk_factors,
                catalysts=catalysts,
                price_target=intrinsic_value,
                time_horizon="3-5 years",
                additional_data={
                    'investment_style': 'Deep Value Investing',
                    'investor_type': analysis_type,
                    'margin_of_safety_required': '30-50%',
                }
            )
            return apply_macro_to_result(result, macro, "graham")
            
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
    
    async def _calculate_graham_metrics(self, financial_data: Dict[str, Any]) -> Dict[str, float]:
        """Calculate Graham-specific financial metrics"""
        info = financial_data.get('info', {})
        financials = financial_data.get('financials', {})
        balance_sheet = financial_data.get('balance_sheet', {})
        
        metrics = {
            'pe_ratio': info.get('trailingPE', 0),
            'pb_ratio': info.get('priceToBook', 0),
            'debt_to_equity': info.get('debtToEquity', 0),
            'dividend_yield': info.get('dividendYield', 0),
            'eps': info.get('trailingEps', 0),
            'book_value': info.get('bookValue', 0),
            'current_price': info.get('currentPrice', 0),
        }
        
        # Calculate additional Graham metrics
        try:
            # Current ratio
            if not balance_sheet.empty:
                current_assets = balance_sheet.loc['Total Current Assets'].iloc[0] if 'Total Current Assets' in balance_sheet.index else 0
                current_liabilities = balance_sheet.loc['Total Current Liabilities'].iloc[0] if 'Total Current Liabilities' in balance_sheet.index else 1
                metrics['current_ratio'] = current_assets / current_liabilities if current_liabilities > 0 else 0
                
                # Net current assets (Current assets - Total liabilities)
                total_liabilities = balance_sheet.loc['Total Liab'].iloc[0] if 'Total Liab' in balance_sheet.index else current_liabilities
                metrics['net_current_assets'] = current_assets - total_liabilities
                
                # Tangible book value
                total_assets = balance_sheet.loc['Total Assets'].iloc[0] if 'Total Assets' in balance_sheet.index else 0
                goodwill = balance_sheet.loc['Good Will'].iloc[0] if 'Good Will' in balance_sheet.index else 0
                intangible_assets = balance_sheet.loc['Intangible Assets'].iloc[0] if 'Intangible Assets' in balance_sheet.index else 0
                metrics['tangible_book_value'] = total_assets - goodwill - intangible_assets - total_liabilities
            else:
                metrics.update({
                    'current_ratio': 0,
                    'net_current_assets': 0,
                    'tangible_book_value': 0,
                })
            
            # Earnings per share growth (simplified)
            if not financials.empty and len(financials.columns) >= 2:
                net_income_1 = financials.loc['Net Income'].iloc[0] if 'Net Income' in financials.index else 0
                net_income_2 = financials.loc['Net Income'].iloc[1] if 'Net Income' in financials.index else 1
                shares_outstanding = info.get('sharesOutstanding', 1)
                
                eps_1 = net_income_1 / shares_outstanding if shares_outstanding > 0 else 0
                eps_2 = net_income_2 / shares_outstanding if shares_outstanding > 0 else 0
                
                if eps_2 > 0:
                    metrics['earnings_growth'] = (eps_1 - eps_2) / abs(eps_2)
                else:
                    metrics['earnings_growth'] = 0
            else:
                metrics['earnings_growth'] = info.get('earningsGrowth', 0)
            
            # Earnings yield (E/P ratio - Graham's preferred metric)
            if metrics['pe_ratio'] > 0:
                metrics['earnings_yield'] = 1.0 / metrics['pe_ratio']
            else:
                metrics['earnings_yield'] = 0
            
        except Exception:
            # Use defaults if calculations fail
            metrics.update({
                'current_ratio': 0,
                'net_current_assets': 0,
                'tangible_book_value': 0,
                'earnings_growth': 0,
                'earnings_yield': 0,
            })
        
        return metrics
    
    async def _net_net_test(self, financial_data: Dict[str, Any]) -> bool:
        """Graham's net-net test: Current assets exceed total liabilities"""
        try:
            balance_sheet = financial_data.get('balance_sheet', {})
            
            if balance_sheet.empty:
                return False
            
            current_assets = balance_sheet.loc['Total Current Assets'].iloc[0] if 'Total Current Assets' in balance_sheet.index else 0
            total_liabilities = balance_sheet.loc['Total Liab'].iloc[0] if 'Total Liab' in balance_sheet.index else 0
            
            return current_assets > total_liabilities
            
        except Exception:
            return False
    
    async def _earnings_power_test(self, financial_data: Dict[str, Any]) -> bool:
        """Test for consistent earnings power"""
        try:
            financials = financial_data.get('financials', {})
            
            if financials.empty or len(financials.columns) < 3:
                return False
            
            # Check last 3 years of positive earnings
            for i in range(min(3, len(financials.columns))):
                net_income = financials.loc['Net Income'].iloc[i] if 'Net Income' in financials.index else 0
                if net_income <= 0:
                    return False
            
            return True
            
        except Exception:
            return False
    
    async def _financial_strength_test(self, financial_data: Dict[str, Any]) -> bool:
        """Test for financial strength using Graham's criteria"""
        try:
            info = financial_data.get('info', {})
            
            # Current ratio ≥ 2
            current_ratio = info.get('currentRatio', 0)
            if current_ratio < 2.0:
                return False
            
            # Debt to equity ≤ 0.5
            debt_to_equity = info.get('debtToEquity', 1.0)
            if debt_to_equity > 0.5:
                return False
            
            return True
            
        except Exception:
            return False
    
    async def _graham_number(self, financial_data: Dict[str, Any]) -> float:
        """Calculate Graham Number: sqrt(22.5 × EPS × Book Value)"""
        try:
            eps = financial_data.get('info', {}).get('trailingEps', 0)
            book_value = financial_data.get('info', {}).get('bookValue', 0)
            
            if eps <= 0 or book_value <= 0:
                return 0
            
            graham_number = np.sqrt(22.5 * eps * book_value)
            return graham_number
            
        except Exception:
            return 0
    
    async def _graham_dcf(self, financial_data: Dict[str, Any]) -> float:
        """Simplified DCF using Graham's conservative assumptions"""
        try:
            eps = financial_data.get('info', {}).get('trailingEps', 0)
            
            if eps <= 0:
                return 0
            
            # Graham's conservative growth assumption: 3% annually
            growth_rate = 0.03
            
            # Graham's required return: 8% (2x AAA bond yield)
            required_return = 0.08
            
            # Simple perpetuity value
            intrinsic_value = eps * (1 + growth_rate) / (required_return - growth_rate)
            
            return intrinsic_value
            
        except Exception:
            return 0
    
    async def _net_net_value(self, financial_data: Dict[str, Any]) -> float:
        """Calculate net-net working capital value per share"""
        try:
            balance_sheet = financial_data.get('balance_sheet', {})
            info = financial_data.get('info', {})
            
            if balance_sheet.empty:
                return 0
            
            # Net-net working capital = Current assets - Total liabilities
            current_assets = balance_sheet.loc['Total Current Assets'].iloc[0] if 'Total Current Assets' in balance_sheet.index else 0
            total_liabilities = balance_sheet.loc['Total Liab'].iloc[0] if 'Total Liab' in balance_sheet.index else 0
            
            net_net_working_capital = current_assets - total_liabilities
            
            shares_outstanding = info.get('sharesOutstanding', 1)
            net_net_per_share = net_net_working_capital / shares_outstanding if shares_outstanding > 0 else 0
            
            return max(net_net_per_share, 0)
            
        except Exception:
            return 0
    
    def _calculate_margin_of_safety(self, intrinsic_value: float, current_price: float) -> float:
        """Calculate margin of safety percentage"""
        if current_price <= 0:
            return 0.0
        
        margin = (intrinsic_value - current_price) / current_price
        return max(margin, 0.0)
    
    def _calculate_graham_confidence(self, metrics: Dict[str, float], criteria: Dict[str, tuple],
                                   net_net_test: bool, earnings_power_test: bool,
                                   financial_strength_test: bool, margin_of_safety: float) -> float:
        """Calculate overall confidence score"""
        # Financial metrics confidence
        financial_confidence = self._calculate_confidence(metrics, criteria)
        
        # Graham's special tests
        test_scores = []
        if net_net_test:
            test_scores.append(0.8)
        if earnings_power_test:
            test_scores.append(0.7)
        if financial_strength_test:
            test_scores.append(0.6)
        
        test_confidence = np.mean(test_scores) if test_scores else 0.3
        
        # Margin of safety (Graham requires 30-50%)
        margin_score = min(margin_of_safety / 0.30, 1.0)
        
        # Weight different factors
        weights = {
            'financial': 0.4,
            'tests': 0.3,
            'margin_of_safety': 0.3
        }
        
        overall_confidence = (
            weights['financial'] * financial_confidence +
            weights['tests'] * test_confidence +
            weights['margin_of_safety'] * margin_score
        )
        
        return overall_confidence
    
    def _get_graham_recommendation(self, confidence: float, margin_of_safety: float, net_net_test: bool) -> Recommendation:
        """Get recommendation based on Graham's criteria"""
        # Graham's special consideration for net-net stocks
        if net_net_test and margin_of_safety >= 0.30:
            return Recommendation.STRONG_BUY
        
        # Standard Graham criteria
        if confidence >= 0.7 and margin_of_safety >= 0.30:
            return Recommendation.STRONG_BUY
        elif confidence >= 0.6 and margin_of_safety >= 0.20:
            return Recommendation.BUY
        elif confidence >= 0.5 and margin_of_safety >= 0.10:
            return Recommendation.HOLD
        elif margin_of_safety < 0 or confidence < 0.3:
            return Recommendation.SELL
        else:
            return Recommendation.HOLD
    
    async def _generate_graham_reasoning(self, ticker: str, metrics: Dict[str, float],
                                       criteria: Dict[str, tuple], net_net_test: bool,
                                       earnings_power_test: bool, financial_strength_test: bool,
                                       margin_of_safety: float, intrinsic_value: float, 
                                       analysis_type: str) -> str:
        """Generate Graham-style reasoning"""
        reasoning_parts = []
        
        # Analysis type
        reasoning_parts.append(f"Analysis based on {analysis_type} criteria.")
        
        # Net-net test
        if net_net_test:
            reasoning_parts.append(f"{ticker} passes the net-net test, indicating significant downside protection.")
        else:
            reasoning_parts.append(f"{ticker} fails the net-net test.")
        
        # Earnings power
        if earnings_power_test:
            reasoning_parts.append("Demonstrates consistent earnings power over multiple years.")
        else:
            reasoning_parts.append("Lacks consistent earnings history.")
        
        # Financial strength
        if financial_strength_test:
            reasoning_parts.append("Strong financial position with adequate liquidity.")
        else:
            reasoning_parts.append("Financial strength appears insufficient.")
        
        # Key metrics assessment
        pe_ratio = metrics.get('pe_ratio', 0)
        if pe_ratio <= 15:
            reasoning_parts.append(f"Attractive P/E ratio of {pe_ratio:.1f} indicates good value.")
        elif pe_ratio <= 20:
            reasoning_parts.append(f"Reasonable P/E ratio of {pe_ratio:.1f}.")
        else:
            reasoning_parts.append(f"High P/E ratio of {pe_ratio:.1f} suggests overvaluation.")
        
        pb_ratio = metrics.get('pb_ratio', 0)
        if pb_ratio <= 1.0:
            reasoning_parts.append(f"Low P/B ratio of {pb_ratio:.1f} provides asset protection.")
        elif pb_ratio <= 1.5:
            reasoning_parts.append(f"Moderate P/B ratio of {pb_ratio:.1f}.")
        else:
            reasoning_parts.append(f"High P/B ratio of {pb_ratio:.1f} raises valuation concerns.")
        
        # Margin of safety
        if margin_of_safety >= 0.50:
            reasoning_parts.append(f"Exceptional margin of safety of {margin_of_safety:.1%} provides significant downside protection.")
        elif margin_of_safety >= 0.30:
            reasoning_parts.append(f"Adequate margin of safety of {margin_of_safety:.1%}.")
        elif margin_of_safety >= 0.10:
            reasoning_parts.append(f"Modest margin of safety of {margin_of_safety:.1%}.")
        elif margin_of_safety < 0:
            reasoning_parts.append("Negative margin of safety indicates overvaluation.")
        
        # Valuation conclusion
        current_price = metrics.get('current_price', 0)
        if intrinsic_value > 0 and current_price > 0:
            reasoning_parts.append(f"Intrinsic value estimated at ${intrinsic_value:.2f} vs current price of ${current_price:.2f}.")
        
        # Graham's philosophy
        if margin_of_safety >= 0.30:
            reasoning_parts.append("This aligns with Graham's principle: 'The intelligent investor is a realist who sells to optimists and buys from pessimists.'")
        
        return " ".join(reasoning_parts)
    
    async def _identify_graham_risks(self, financial_data: Dict[str, Any], 
                                    metrics: Dict[str, float]) -> list:
        """Identify Graham-specific risk factors"""
        risks = []
        
        # High valuation risk
        pe_ratio = metrics.get('pe_ratio', 0)
        if pe_ratio > 25:
            risks.append("P/E ratio too high for value investor")
        elif pe_ratio > 20:
            risks.append("Elevated P/E ratio")
        
        pb_ratio = metrics.get('pb_ratio', 0)
        if pb_ratio > 2.0:
            risks.append("P/B ratio excessive for value investing")
        elif pb_ratio > 1.5:
            risks.append("High P/B ratio")
        
        # Weak balance sheet
        current_ratio = metrics.get('current_ratio', 0)
        if current_ratio < 1.5:
            risks.append("Inadequate current ratio")
        elif current_ratio < 2.0:
            risks.append("Current ratio below Graham's preferred level")
        
        debt_to_equity = metrics.get('debt_to_equity', 0)
        if debt_to_equity > 1.0:
            risks.append("Excessive debt levels")
        elif debt_to_equity > 0.5:
            risks.append("Debt levels above Graham's preference")
        
        # No dividend
        dividend_yield = metrics.get('dividend_yield', 0)
        if dividend_yield == 0:
            risks.append("No dividend payment")
        elif dividend_yield < 0.02:
            risks.append("Dividend yield below 2%")
        
        # Negative earnings
        eps = metrics.get('eps', 0)
        if eps < 0:
            risks.append("Negative earnings")
        
        # Fails net-net test
        if not metrics.get('net_net_test', False):
            risks.append("Fails net-net working capital test")
        
        return risks
    
    async def _identify_graham_catalysts(self, financial_data: Dict[str, Any], 
                                        metrics: Dict[str, float]) -> list:
        """Identify Graham-specific positive catalysts"""
        catalysts = []
        
        # Net-net opportunity
        if metrics.get('net_net_test', False):
            catalysts.append("Net-net working capital opportunity")
        
        # Attractive valuation
        pe_ratio = metrics.get('pe_ratio', 0)
        if pe_ratio < 10:
            catalysts.append("Very low P/E ratio")
        elif pe_ratio < 15:
            catalysts.append("Attractive P/E ratio")
        
        pb_ratio = metrics.get('pb_ratio', 0)
        if pb_ratio < 1.0:
            catalysts.append("Trading below book value")
        elif pb_ratio < 1.2:
            catalysts.append("Reasonable P/B ratio")
        
        # Strong balance sheet
        current_ratio = metrics.get('current_ratio', 0)
        if current_ratio > 3.0:
            catalysts.append("Excellent liquidity")
        elif current_ratio > 2.0:
            catalysts.append("Strong current ratio")
        
        debt_to_equity = metrics.get('debt_to_equity', 0)
        if debt_to_equity < 0.2:
            catalysts.append("Conservative debt levels")
        elif debt_to_equity < 0.5:
            catalysts.append("Reasonable debt levels")
        
        # Dividend income
        dividend_yield = metrics.get('dividend_yield', 0)
        if dividend_yield > 0.04:
            catalysts.append("High dividend yield")
        elif dividend_yield > 0.02:
            catalysts.append("Adequate dividend yield")
        
        # Margin of safety
        margin_of_safety = metrics.get('margin_of_safety', 0)
        if margin_of_safety > 0.50:
            catalysts.append("Exceptional margin of safety")
        elif margin_of_safety > 0.30:
            catalysts.append("Adequate margin of safety")
        
        return catalysts
