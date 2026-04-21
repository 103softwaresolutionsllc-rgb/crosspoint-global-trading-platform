"""
Peter Lynch Agent
Based on Peter Lynch's growth investing principles:
- "Invest in what you know"
- 10-bagger potential
- PEG ratio analysis
- Growth at reasonable price (GARP)
- Story behind the stock
- Buy what you understand
"""

import asyncio
from typing import Dict, Any
import numpy as np

from ..base import BaseAgent, AgentResult, AgentType, Recommendation


class LynchAgent(BaseAgent):
    """
    Peter Lynch AI Agent implementing his growth investing philosophy:
    
    Core Principles:
    1. Invest in what you know (circle of competence)
    2. Look for 10-baggers (10x returns)
    3. PEG ratio < 1.0 for growth stocks
    4. Growth at reasonable price (GARP)
    5. Understand the business story
    6. Buy good businesses, not just good stocks
    7. Long-term perspective (5-10 years)
    """
    
    def __init__(self):
        super().__init__("Peter Lynch", AgentType.VALUE_INVESTOR)
        
        # Lynch's key criteria thresholds
        self.thresholds = {
            'peg_ratio': (0, 1.0),  # PEG < 1.0
            'pe_ratio': (5, 30),  # P/E between 5-30 for growth stocks
            'revenue_growth': (0.10, 0.50),  # Revenue growth 10-50%
            'earnings_growth': (0.15, 0.50),  # Earnings growth 15-50%
            'debt_to_equity': (0, 1.0),  # Debt/Equity < 1.0
            'roe': (0.15, 1.0),  # ROE > 15%
            'profit_margin': (0.05, 0.30),  # Profit margin 5-30%
        }
        
    async def analyze(self, ticker: str, **kwargs) -> AgentResult:
        """Analyze stock using Peter Lynch's principles"""
        try:
            # Get financial data
            financial_data = await self._get_financial_data(ticker)
            
            # Calculate Lynch-specific metrics
            lynch_metrics = await self._calculate_lynch_metrics(financial_data)
            
            # Assess growth story
            growth_story = await self._assess_growth_story(ticker, financial_data)
            
            # Calculate 10-bagger potential
            tenbagger_potential = await self._calculate_tenbagger_potential(financial_data, lynch_metrics)
            
            # Evaluate business understanding
            business_score = await self._evaluate_business_understanding(ticker, financial_data)
            
            # Calculate intrinsic value using Lynch's methods
            intrinsic_value = await self._lynch_intrinsic_value(financial_data, lynch_metrics)
            
            # Calculate growth at reasonable price (GARP) score
            garp_score = self._calculate_garp_score(lynch_metrics)
            
            # Get overall confidence
            confidence = self._calculate_lynch_confidence(
                lynch_metrics, growth_story, tenbagger_potential, 
                business_score, garp_score
            )
            
            # Generate recommendation
            recommendation = self._get_lynch_recommendation(confidence, tenbagger_potential, garp_score)
            
            # Create reasoning
            reasoning = await self._generate_lynch_reasoning(
                ticker, lynch_metrics, growth_story, tenbagger_potential,
                business_score, garp_score, intrinsic_value
            )
            
            # Identify risk factors and catalysts
            risk_factors = await self._identify_lynch_risks(financial_data, lynch_metrics)
            catalysts = await self._identify_lynch_catalysts(financial_data, lynch_metrics)
            
            return AgentResult(
                agent_name=self.name,
                ticker=ticker.upper(),
                recommendation=recommendation,
                confidence=confidence,
                reasoning=reasoning,
                key_metrics={
                    **lynch_metrics,
                    'growth_story_score': growth_story,
                    'tenbagger_potential': tenbagger_potential,
                    'business_score': business_score,
                    'garp_score': garp_score,
                    'intrinsic_value': intrinsic_value,
                },
                risk_factors=risk_factors,
                catalysts=catalysts,
                price_target=intrinsic_value,
                time_horizon="5-10 years",
                additional_data={
                    'investment_style': 'Growth at Reasonable Price (GARP)',
                    'philosophy': 'Buy what you know',
                    'target_return': '10x potential (10-bagger)',
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
    
    async def _calculate_lynch_metrics(self, financial_data: Dict[str, Any]) -> Dict[str, float]:
        """Calculate Lynch-specific financial metrics"""
        info = financial_data.get('info', {})
        financials = financial_data.get('financials', {})
        
        metrics = {
            'pe_ratio': info.get('trailingPE', 0),
            'pb_ratio': info.get('priceToBook', 0),
            'debt_to_equity': info.get('debtToEquity', 0),
            'roe': info.get('returnOnEquity', 0),
            'profit_margin': info.get('profitMargins', 0),
            'operating_margin': info.get('operatingMargins', 0),
            'revenue_growth': info.get('revenueGrowth', 0),
            'earnings_growth': info.get('earningsGrowth', 0),
            'eps': info.get('trailingEps', 0),
            'current_price': info.get('currentPrice', 0),
        }
        
        # Calculate PEG ratio (Lynch's favorite metric)
        pe_ratio = metrics['pe_ratio']
        earnings_growth = metrics['earnings_growth']
        
        if pe_ratio > 0 and earnings_growth > 0:
            metrics['peg_ratio'] = pe_ratio / (earnings_growth * 100)  # Convert to decimal
        else:
            metrics['peg_ratio'] = float('inf')
        
        # Calculate additional Lynch metrics
        try:
            # Revenue growth rate (5-year average if available)
            if not financials.empty and len(financials.columns) >= 5:
                revenues = [financials.loc['Total Revenue'].iloc[i] for i in range(min(5, len(financials.columns)))]
                if len(revenues) >= 2:
                    cagr = (revenues[0] / revenues[-1]) ** (1/len(revenues)) - 1
                    metrics['revenue_cagr'] = cagr
                else:
                    metrics['revenue_cagr'] = info.get('revenueGrowth', 0)
            else:
                metrics['revenue_cagr'] = info.get('revenueGrowth', 0)
            
            # Earnings growth consistency
            if not financials.empty and len(financials.columns) >= 3:
                net_incomes = []
                for i in range(min(3, len(financials.columns))):
                    net_income = financials.loc['Net Income'].iloc[i] if 'Net Income' in financials.index else 0
                    net_incomes.append(net_income)
                
                # Check if earnings are consistently growing
                consistent_growth = all(net_incomes[i] > net_incomes[i+1] for i in range(len(net_incomes)-1))
                metrics['consistent_earnings_growth'] = 1.0 if consistent_growth else 0.0
            else:
                metrics['consistent_earnings_growth'] = 0.0
            
            # Price-to-sales ratio (Lynch liked this for growth stocks)
            market_cap = info.get('marketCap', 0)
            revenue = info.get('totalRevenue', 0)
            
            if revenue > 0:
                metrics['price_to_sales'] = market_cap / revenue
            else:
                metrics['price_to_sales'] = 0
            
            # Quarterly earnings growth (more recent indicator)
            quarterly_growth = info.get('earningsQuarterlyGrowth', 0)
            metrics['quarterly_earnings_growth'] = quarterly_growth / 100 if quarterly_growth else 0
            
        except Exception:
            # Use defaults if calculations fail
            metrics.update({
                'peg_ratio': float('inf'),
                'revenue_cagr': 0,
                'consistent_earnings_growth': 0,
                'price_to_sales': 0,
                'quarterly_earnings_growth': 0,
            })
        
        return metrics
    
    async def _assess_growth_story(self, ticker: str, financial_data: Dict[str, Any]) -> float:
        """Assess the growth story behind the stock (0-1 scale)"""
        story_factors = []
        
        info = financial_data.get('info', {})
        
        # Revenue growth story
        revenue_growth = info.get('revenueGrowth', 0)
        if revenue_growth > 0.30:
            story_factors.append(0.9)
        elif revenue_growth > 0.20:
            story_factors.append(0.7)
        elif revenue_growth > 0.10:
            story_factors.append(0.5)
        elif revenue_growth > 0.05:
            story_factors.append(0.3)
        else:
            story_factors.append(0.1)
        
        # Earnings growth story
        earnings_growth = info.get('earningsGrowth', 0)
        if earnings_growth > 0.30:
            story_factors.append(0.9)
        elif earnings_growth > 0.20:
            story_factors.append(0.7)
        elif earnings_growth > 0.15:
            story_factors.append(0.5)
        elif earnings_growth > 0.10:
            story_factors.append(0.3)
        else:
            story_factors.append(0.1)
        
        # Market position (simplified by market cap and sector)
        market_cap = info.get('marketCap', 0)
        sector = info.get('sector', '').lower()
        
        # Growth sectors get bonus points
        growth_sectors = ['technology', 'healthcare', 'consumer discretionary', 'communication services']
        if any(growth_sector in sector for growth_sector in growth_sectors):
            story_factors.append(0.7)
        else:
            story_factors.append(0.4)
        
        # Market size (medium companies often have more growth room)
        if 1e9 < market_cap < 50e9:  # $1B to $50B
            story_factors.append(0.8)
        elif market_cap < 1e9:  # Small cap
            story_factors.append(0.6)
        elif market_cap < 10e9:  # Mid cap
            story_factors.append(0.5)
        else:  # Large cap
            story_factors.append(0.3)
        
        # Innovation potential (simplified by R&D expenses if available)
        # This would need more detailed financial data in practice
        story_factors.append(0.5)  # Neutral score
        
        return np.mean(story_factors)
    
    async def _calculate_tenbagger_potential(self, financial_data: Dict[str, Any], 
                                         lynch_metrics: Dict[str, float]) -> float:
        """Calculate potential for 10x returns (0-1 scale)"""
        potential_factors = []
        
        # High growth potential
        revenue_growth = lynch_metrics.get('revenue_cagr', 0)
        if revenue_growth > 0.30:
            potential_factors.append(0.9)
        elif revenue_growth > 0.20:
            potential_factors.append(0.7)
        elif revenue_growth > 0.15:
            potential_factors.append(0.5)
        elif revenue_growth > 0.10:
            potential_factors.append(0.3)
        else:
            potential_factors.append(0.1)
        
        # Reasonable valuation (Lynch's PEG rule)
        peg_ratio = lynch_metrics.get('peg_ratio', float('inf'))
        if peg_ratio < 0.5:
            potential_factors.append(0.9)
        elif peg_ratio < 0.8:
            potential_factors.append(0.7)
        elif peg_ratio < 1.0:
            potential_factors.append(0.5)
        elif peg_ratio < 1.5:
            potential_factors.append(0.3)
        else:
            potential_factors.append(0.1)
        
        # Strong profitability
        roe = lynch_metrics.get('roe', 0)
        if roe > 0.25:
            potential_factors.append(0.8)
        elif roe > 0.20:
            potential_factors.append(0.6)
        elif roe > 0.15:
            potential_factors.append(0.4)
        else:
            potential_factors.append(0.2)
        
        # Large addressable market (simplified)
        info = financial_data.get('info', {})
        sector = info.get('sector', '').lower()
        
        # Sectors with large potential markets
        large_market_sectors = ['technology', 'healthcare', 'consumer discretionary', 'financial services']
        if any(sector in large_market_sectors for sector in large_market_sectors):
            potential_factors.append(0.7)
        else:
            potential_factors.append(0.4)
        
        # Management execution (simplified by consistent earnings)
        consistent_growth = lynch_metrics.get('consistent_earnings_growth', 0)
        potential_factors.append(consistent_growth)
        
        return np.mean(potential_factors)
    
    async def _evaluate_business_understanding(self, ticker: str, financial_data: Dict[str, Any]) -> float:
        """Evaluate how understandable the business is (0-1 scale)"""
        understanding_factors = []
        
        info = financial_data.get('info', {})
        
        # Business simplicity (simplified by sector)
        sector = info.get('sector', '').lower()
        industry = info.get('industry', '').lower()
        
        # Simple businesses to understand
        simple_businesses = ['retail', 'consumer goods', 'food', 'beverages', 'restaurants']
        if any(business in industry for business in simple_businesses):
            understanding_factors.append(0.9)
        elif any(business in sector for business in simple_businesses):
            understanding_factors.append(0.7)
        else:
            understanding_factors.append(0.5)
        
        # Business model clarity (simplified by business summary)
        # In practice, this would analyze the business description
        long_biz_summary = info.get('longBusinessSummary', '')
        if len(long_biz_summary) > 200:
            understanding_factors.append(0.6)  # Detailed description available
        else:
            understanding_factors.append(0.4)
        
        # Financial transparency (simplified by data availability)
        if info.get('trailingPE', 0) > 0 and info.get('returnOnEquity', 0) > 0:
            understanding_factors.append(0.8)
        else:
            understanding_factors.append(0.4)
        
        # Competitive position (simplified by market cap)
        market_cap = info.get('marketCap', 0)
        if market_cap > 10e9:  # Established company
            understanding_factors.append(0.7)
        elif market_cap > 1e9:  # Known company
            understanding_factors.append(0.6)
        else:
            understanding_factors.append(0.4)
        
        return np.mean(understanding_factors)
    
    async def _lynch_intrinsic_value(self, financial_data: Dict[str, Any], 
                                   lynch_metrics: Dict[str, float]) -> float:
        """Calculate intrinsic value using Lynch's methods"""
        try:
            info = financial_data.get('info', {})
            current_price = info.get('currentPrice', 0)
            
            # Method 1: PEG-based valuation
            peg_ratio = lynch_metrics.get('peg_ratio', float('inf'))
            earnings_growth = lynch_metrics.get('earnings_growth', 0)
            eps = lynch_metrics.get('eps', 0)
            
            if peg_ratio < float('inf') and eps > 0:
                # Fair P/E = earnings growth rate
                fair_pe = earnings_growth * 100
                peg_value = eps * fair_pe
            else:
                peg_value = 0
            
            # Method 2: Price-to-sales for growth stocks
            price_to_sales = lynch_metrics.get('price_to_sales', 0)
            revenue = info.get('totalRevenue', 0)
            shares_outstanding = info.get('sharesOutstanding', 1)
            
            if revenue > 0 and shares_outstanding > 0:
                revenue_per_share = revenue / shares_outstanding
                # Lynch liked P/S < 1 for growth stocks
                ps_value = revenue_per_share * 0.8
            else:
                ps_value = 0
            
            # Method 3: Growth-adjusted P/E
            pe_ratio = lynch_metrics.get('pe_ratio', 0)
            if pe_ratio > 0 and eps > 0:
                # Adjust P/E for growth rate
                growth_adjusted_pe = pe_ratio / (1 + earnings_growth)
                growth_value = eps * growth_adjusted_pe * 20  # Normalize to reasonable P/E
            else:
                growth_value = 0
            
            # Method 4: Conservative DCF (Lynch was conservative despite growth focus)
            if eps > 0:
                # Assume 10 years of 15% growth, then 3% terminal
                future_eps = eps * (1.15) ** 10
                terminal_value = future_eps * 15  # 15x terminal P/E
                present_value = terminal_value / (1.15) ** 10
                dcf_value = present_value
            else:
                dcf_value = 0
            
            # Combine methods
            intrinsic_values = [v for v in [peg_value, ps_value, growth_value, dcf_value] if v > 0]
            
            if intrinsic_values:
                # Use weighted average favoring PEG for growth stocks
                weights = [0.4, 0.2, 0.2, 0.2]  # Favor PEG method
                intrinsic_value = np.average(intrinsic_values[:len(weights)], weights=weights[:len(intrinsic_values)])
            else:
                intrinsic_value = current_price
            
            return intrinsic_value
            
        except Exception:
            return financial_data.get('current_price', 0)
    
    def _calculate_garp_score(self, lynch_metrics: Dict[str, float]) -> float:
        """Calculate Growth At Reasonable Price score"""
        garp_factors = []
        
        # PEG ratio (most important for GARP)
        peg_ratio = lynch_metrics.get('peg_ratio', float('inf'))
        if peg_ratio < 0.5:
            garp_factors.append(1.0)
        elif peg_ratio < 0.8:
            garp_factors.append(0.8)
        elif peg_ratio < 1.0:
            garp_factors.append(0.6)
        elif peg_ratio < 1.5:
            garp_factors.append(0.4)
        else:
            garp_factors.append(0.2)
        
        # P/E ratio relative to growth
        pe_ratio = lynch_metrics.get('pe_ratio', 0)
        earnings_growth = lynch_metrics.get('earnings_growth', 0)
        
        if earnings_growth > 0:
            pe_to_growth = pe_ratio / (earnings_growth * 100)
            if pe_to_growth < 0.8:
                garp_factors.append(0.9)
            elif pe_to_growth < 1.0:
                garp_factors.append(0.7)
            elif pe_to_growth < 1.5:
                garp_factors.append(0.5)
            else:
                garp_factors.append(0.3)
        else:
            garp_factors.append(0.2)
        
        # Revenue growth consistency
        revenue_cagr = lynch_metrics.get('revenue_cagr', 0)
        if revenue_cagr > 0.20:
            garp_factors.append(0.8)
        elif revenue_cagr > 0.15:
            garp_factors.append(0.6)
        elif revenue_cagr > 0.10:
            garp_factors.append(0.4)
        else:
            garp_factors.append(0.2)
        
        # Profitability
        roe = lynch_metrics.get('roe', 0)
        if roe > 0.20:
            garp_factors.append(0.8)
        elif roe > 0.15:
            garp_factors.append(0.6)
        elif roe > 0.10:
            garp_factors.append(0.4)
        else:
            garp_factors.append(0.2)
        
        return np.mean(garp_factors)
    
    def _calculate_lynch_confidence(self, lynch_metrics: Dict[str, float],
                                  growth_story: float, tenbagger_potential: float,
                                  business_score: float, garp_score: float) -> float:
        """Calculate overall confidence score"""
        # Financial metrics confidence
        financial_confidence = self._calculate_confidence(lynch_metrics, self.thresholds)
        
        # Weight different factors according to Lynch's priorities
        weights = {
            'financial': 0.25,
            'growth_story': 0.20,
            'tenbagger_potential': 0.20,
            'business_understanding': 0.15,
            'garp_score': 0.20
        }
        
        overall_confidence = (
            weights['financial'] * financial_confidence +
            weights['growth_story'] * growth_story +
            weights['tenbagger_potential'] * tenbagger_potential +
            weights['business_understanding'] * business_score +
            weights['garp_score'] * garp_score
        )
        
        return overall_confidence
    
    def _get_lynch_recommendation(self, confidence: float, tenbagger_potential: float, 
                                 garp_score: float) -> Recommendation:
        """Get recommendation based on Lynch's criteria"""
        # Lynch loved high potential growth stocks at reasonable prices
        if confidence >= 0.7 and tenbagger_potential >= 0.7 and garp_score >= 0.6:
            return Recommendation.STRONG_BUY
        elif confidence >= 0.6 and tenbagger_potential >= 0.5 and garp_score >= 0.5:
            return Recommendation.BUY
        elif confidence >= 0.5 and garp_score >= 0.4:
            return Recommendation.HOLD
        elif garp_score < 0.3 or confidence < 0.3:
            return Recommendation.SELL
        else:
            return Recommendation.HOLD
    
    async def _generate_lynch_reasoning(self, ticker: str, lynch_metrics: Dict[str, float],
                                       growth_story: float, tenbagger_potential: float,
                                       business_score: float, garp_score: float,
                                       intrinsic_value: float) -> str:
        """Generate Lynch-style reasoning"""
        reasoning_parts = []
        
        # Growth story assessment
        if growth_story > 0.7:
            reasoning_parts.append(f"{ticker} has a compelling growth story with strong expansion potential.")
        elif growth_story > 0.5:
            reasoning_parts.append(f"{ticker} shows moderate growth characteristics.")
        else:
            reasoning_parts.append(f"{ticker} lacks a clear growth story.")
        
        # 10-bagger potential
        if tenbagger_potential > 0.7:
            reasoning_parts.append("Significant 10-bagger potential exists based on growth metrics and market opportunity.")
        elif tenbagger_potential > 0.5:
            reasoning_parts.append("Good potential for multi-bagger returns.")
        elif tenbagger_potential > 0.3:
            reasoning_parts.append("Moderate return potential.")
        else:
            reasoning_parts.append("Limited 10-bagger potential.")
        
        # PEG analysis (Lynch's favorite)
        peg_ratio = lynch_metrics.get('peg_ratio', float('inf'))
        if peg_ratio < 0.5:
            reasoning_parts.append(f"Excellent PEG ratio of {peg_ratio:.2f} indicates significant undervaluation relative to growth.")
        elif peg_ratio < 1.0:
            reasoning_parts.append(f"Attractive PEG ratio of {peg_ratio:.2f} suggests reasonable valuation.")
        elif peg_ratio < 1.5:
            reasoning_parts.append(f"PEG ratio of {peg_ratio:.2f} is acceptable for growth stock.")
        else:
            reasoning_parts.append(f"High PEG ratio of {peg_ratio:.2f} suggests overvaluation.")
        
        # Business understanding
        if business_score > 0.7:
            reasoning_parts.append("Business model is simple and easy to understand.")
        elif business_score > 0.5:
            reasoning_parts.append("Business is reasonably understandable.")
        else:
            reasoning_parts.append("Complex business model makes analysis difficult.")
        
        # Growth metrics
        revenue_growth = lynch_metrics.get('revenue_cagr', 0)
        if revenue_growth > 0.20:
            reasoning_parts.append(f"Strong revenue growth of {revenue_growth:.1%} demonstrates expanding business.")
        elif revenue_growth > 0.15:
            reasoning_parts.append(f"Solid revenue growth of {revenue_growth:.1%}.")
        
        earnings_growth = lynch_metrics.get('earnings_growth', 0)
        if earnings_growth > 0.25:
            reasoning_parts.append(f"Exceptional earnings growth of {earnings_growth:.1%}.")
        elif earnings_growth > 0.15:
            reasoning_parts.append(f"Good earnings growth of {earnings_growth:.1%}.")
        
        # Valuation conclusion
        current_price = lynch_metrics.get('current_price', 0)
        if intrinsic_value > 0 and current_price > 0:
            reasoning_parts.append(f"Intrinsic value estimated at ${intrinsic_value:.2f} vs current price of ${current_price:.2f}.")
        
        # Lynch's philosophy
        if garp_score > 0.6:
            reasoning_parts.append("This represents the classic 'Growth At Reasonable Price' opportunity that Lynch favored.")
        
        return " ".join(reasoning_parts)
    
    async def _identify_lynch_risks(self, financial_data: Dict[str, Any], 
                                   lynch_metrics: Dict[str, float]) -> list:
        """Identify Lynch-specific risk factors"""
        risks = []
        
        # High PEG ratio
        peg_ratio = lynch_metrics.get('peg_ratio', float('inf'))
        if peg_ratio > 2.0:
            risks.append("Very high PEG ratio suggests overvaluation")
        elif peg_ratio > 1.5:
            risks.append("High PEG ratio for growth stock")
        
        # Low growth
        revenue_growth = lynch_metrics.get('revenue_cagr', 0)
        if revenue_growth < 0.05:
            risks.append("Insufficient revenue growth for growth strategy")
        elif revenue_growth < 0.10:
            risks.append("Modest revenue growth")
        
        earnings_growth = lynch_metrics.get('earnings_growth', 0)
        if earnings_growth < 0.10:
            risks.append("Low earnings growth")
        elif earnings_growth < 0.15:
            risks.append("Moderate earnings growth")
        
        # Complex business
        business_score = lynch_metrics.get('business_score', 0)
        if business_score < 0.4:
            risks.append("Complex business model")
        
        # High valuation
        pe_ratio = lynch_metrics.get('pe_ratio', 0)
        if pe_ratio > 50:
            risks.append("Extremely high P/E ratio")
        elif pe_ratio > 30:
            risks.append("High P/E ratio for growth stock")
        
        # Low profitability
        roe = lynch_metrics.get('roe', 0)
        if roe < 0.10:
            risks.append("Low return on equity")
        elif roe < 0.15:
            risks.append("Modest ROE for growth stock")
        
        # Inconsistent earnings
        if lynch_metrics.get('consistent_earnings_growth', 0) < 0.5:
            risks.append("Inconsistent earnings growth")
        
        return risks
    
    async def _identify_lynch_catalysts(self, financial_data: Dict[str, Any], 
                                       lynch_metrics: Dict[str, float]) -> list:
        """Identify Lynch-specific positive catalysts"""
        catalysts = []
        
        # Low PEG ratio
        peg_ratio = lynch_metrics.get('peg_ratio', float('inf'))
        if peg_ratio < 0.5:
            catalysts.append("Very attractive PEG ratio")
        elif peg_ratio < 1.0:
            catalysts.append("Good PEG ratio")
        
        # High growth
        revenue_growth = lynch_metrics.get('revenue_cagr', 0)
        if revenue_growth > 0.25:
            catalysts.append("Exceptional revenue growth")
        elif revenue_growth > 0.20:
            catalysts.append("Strong revenue growth")
        elif revenue_growth > 0.15:
            catalysts.append("Good revenue growth")
        
        earnings_growth = lynch_metrics.get('earnings_growth', 0)
        if earnings_growth > 0.30:
            catalysts.append("Exceptional earnings growth")
        elif earnings_growth > 0.20:
            catalysts.append("Strong earnings growth")
        
        # High 10-bagger potential
        tenbagger_potential = lynch_metrics.get('tenbagger_potential', 0)
        if tenbagger_potential > 0.7:
            catalysts.append("Significant 10-bagger potential")
        elif tenbagger_potential > 0.5:
            catalysts.append("Good multi-bagger potential")
        
        # Simple business
        business_score = lynch_metrics.get('business_score', 0)
        if business_score > 0.7:
            catalysts.append("Simple, understandable business")
        
        # Strong profitability
        roe = lynch_metrics.get('roe', 0)
        if roe > 0.25:
            catalysts.append("Exceptional return on equity")
        elif roe > 0.20:
            catalysts.append("Strong return on equity")
        
        # Consistent earnings
        if lynch_metrics.get('consistent_earnings_growth', 0) > 0.8:
            catalysts.append("Consistent earnings growth")
        
        # Reasonable valuation
        garp_score = lynch_metrics.get('garp_score', 0)
        if garp_score > 0.7:
            catalysts.append("Excellent growth at reasonable price")
        elif garp_score > 0.5:
            catalysts.append("Good growth at reasonable price")
        
        return catalysts
