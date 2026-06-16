"""
Base Agent Framework for AI Trading Agents
"""

import asyncio
import abc
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from enum import Enum

import numpy as np
import pandas as pd
import yfinance as yf
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic


class AgentType(Enum):
    """Agent type enumeration"""
    VALUE_INVESTOR = "value_investor"
    GROWTH_INVESTOR = "growth_investor"
    QUANT_AGENT = "quant_agent"
    MACRO_AGENT = "macro_agent"
    GEOPOLITICAL_AGENT = "geopolitical_agent"


class Recommendation(Enum):
    """Investment recommendation types"""
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"


@dataclass
class AgentResult:
    """Result from agent analysis"""
    agent_name: str
    ticker: str
    recommendation: Recommendation
    confidence: float  # 0.0 to 1.0
    reasoning: str
    key_metrics: Dict[str, float]
    risk_factors: List[str]
    catalysts: List[str]
    price_target: Optional[float] = None
    time_horizon: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None


class BaseAgent(abc.ABC):
    """
    Abstract base class for all AI trading agents.
    
    Each agent implements specific investment philosophies and strategies
    based on famous investors, quantitative models, or economic frameworks.
    """
    
    def __init__(self, name: str, agent_type: AgentType):
        self.name = name
        self.agent_type = agent_type
        self.llm_provider = "openai"  # Default provider
        self.model_name = "gpt-4-turbo-preview"
        self.temperature = 0.3  # Lower temperature for more consistent analysis
        
        # Initialize LLM clients
        self.openai_client = None
        self.anthropic_client = None
        
    async def _initialize_llm_clients(self):
        """Initialize LLM clients based on provider"""
        if self.llm_provider == "openai":
            self.openai_client = AsyncOpenAI()
        elif self.llm_provider == "anthropic":
            self.anthropic_client = AsyncAnthropic()
    
    @abc.abstractmethod
    async def analyze(self, ticker: str, **kwargs) -> AgentResult:
        """
        Analyze a stock and return investment recommendation.
        
        Args:
            ticker: Stock ticker symbol
            **kwargs: Additional parameters specific to agent
            
        Returns:
            AgentResult with recommendation and analysis
        """
        pass
    
    async def _get_financial_data(self, ticker: str) -> Dict[str, Any]:
        """Get comprehensive financial data for analysis"""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Get price data
            price_data = stock.history(period="2y")
            
            # Get financial statements
            financials = stock.financials
            balance_sheet = stock.balance_sheet
            cash_flow = stock.cashflow
            
            return {
                'info': info,
                'price_data': price_data,
                'financials': financials,
                'balance_sheet': balance_sheet,
                'cash_flow': cash_flow,
                'current_price': info.get('currentPrice', 0),
                'market_cap': info.get('marketCap', 0),
                'pe_ratio': info.get('trailingPE', 0),
                'pb_ratio': info.get('priceToBook', 0),
                'dividend_yield': info.get('dividendYield', 0),
                'beta': info.get('beta', 1.0),
                'eps': info.get('trailingEps', 0),
                'revenue': info.get('totalRevenue', 0),
                'net_income': info.get('netIncomeToCommon', 0),
                'book_value': info.get('bookValue', 0),
                'debt_to_equity': info.get('debtToEquity', 0),
                'roe': info.get('returnOnEquity', 0),
                'roa': info.get('returnOnAssets', 0),
                'profit_margin': info.get('profitMargins', 0),
                'operating_margin': info.get('operatingMargins', 0),
            }
            
        except Exception as e:
            raise ValueError(f"Failed to get financial data for {ticker}: {str(e)}")
    
    async def _calculate_technical_indicators(self, price_data: pd.DataFrame) -> Dict[str, float]:
        """Calculate technical analysis indicators"""
        try:
            close_prices = price_data['Close']
            
            # Moving averages
            ma_50 = close_prices.rolling(window=50).mean().iloc[-1]
            ma_200 = close_prices.rolling(window=200).mean().iloc[-1]
            current_price = close_prices.iloc[-1]
            
            # RSI
            delta = close_prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs)).iloc[-1]
            
            # MACD
            exp1 = close_prices.ewm(span=12).mean()
            exp2 = close_prices.ewm(span=26).mean()
            macd = exp1 - exp2
            signal = macd.ewm(span=9).mean()
            macd_histogram = macd - signal
            
            # Bollinger Bands
            bb_period = 20
            bb_std = 2
            bb_middle = close_prices.rolling(window=bb_period).mean()
            bb_std_dev = close_prices.rolling(window=bb_period).std()
            bb_upper = bb_middle + (bb_std_dev * bb_std)
            bb_lower = bb_middle - (bb_std_dev * bb_std)
            
            return {
                'current_price': current_price,
                'ma_50': ma_50,
                'ma_200': ma_200,
                'price_above_ma_50': current_price > ma_50,
                'price_above_ma_200': current_price > ma_200,
                'ma_50_above_ma_200': ma_50 > ma_200,
                'rsi': rsi,
                'rsi_overbought': rsi > 70,
                'rsi_oversold': rsi < 30,
                'macd': macd.iloc[-1],
                'macd_signal': signal.iloc[-1],
                'macd_histogram': macd_histogram.iloc[-1],
                'macd_bullish': macd.iloc[-1] > signal.iloc[-1],
                'bb_upper': bb_upper.iloc[-1],
                'bb_middle': bb_middle.iloc[-1],
                'bb_lower': bb_lower.iloc[-1],
                'bb_position': (current_price - bb_lower.iloc[-1]) / (bb_upper.iloc[-1] - bb_lower.iloc[-1]),
            }
            
        except Exception as e:
            raise ValueError(f"Failed to calculate technical indicators: {str(e)}")

    async def _structural_regime_check(self, ticker: str, price_data: pd.DataFrame) -> dict[str, float]:
        """
        MIT-style econometric guard: detect statistical breaks in rolling variance.
        Returns dampening factor (1.0 = no change, lower = reduce agent confidence).
        """
        closes = price_data["Close"].dropna()
        if len(closes) < 60:
            return {"dampening": 1.0, "z_score": 0.0, "vol_ratio": 1.0}

        returns = closes.pct_change().dropna()
        short_vol = float(returns.tail(20).std())
        long_vol = float(returns.tail(120).std()) if len(returns) >= 120 else float(returns.std())
        vol_ratio = short_vol / long_vol if long_vol > 0 else 1.0

        recent = float(returns.tail(20).mean())
        baseline = float(returns.tail(120).mean()) if len(returns) >= 120 else float(returns.mean())
        baseline_std = float(returns.tail(120).std()) if len(returns) >= 120 else float(returns.std())
        z_score = (recent - baseline) / baseline_std if baseline_std > 0 else 0.0

        dampening = 1.0
        if vol_ratio > 2.0:
            dampening *= 0.75
        if abs(z_score) > 2.5:
            dampening *= 0.80
        if vol_ratio > 3.0 or abs(z_score) > 3.5:
            dampening *= 0.70

        return {
            "dampening": max(0.4, dampening),
            "z_score": z_score,
            "vol_ratio": vol_ratio,
            "short_vol": short_vol,
            "long_vol": long_vol,
        }

    def _apply_structural_dampening(
        self, result: AgentResult, regime: dict[str, float]
    ) -> AgentResult:
        """Apply structural break dampening to confidence and annotate risks."""
        from dataclasses import replace

        factor = regime.get("dampening", 1.0)
        if factor >= 0.99:
            return result

        new_conf = max(0.0, min(1.0, result.confidence * factor))
        note = (
            f"Structural regime check: vol_ratio={regime.get('vol_ratio', 0):.2f}, "
            f"z={regime.get('z_score', 0):.2f} — confidence dampened to {new_conf:.2f}"
        )
        risks = list(result.risk_factors) + [note]
        add = dict(result.additional_data or {})
        add["structural_regime"] = regime
        return replace(result, confidence=new_conf, risk_factors=risks, additional_data=add)

    async def _get_llm_analysis(self, prompt: str) -> str:
        """Get analysis from language model"""
        try:
            await self._initialize_llm_clients()
            
            if self.llm_provider == "openai" and self.openai_client:
                response = await self.openai_client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": "You are an expert financial analyst providing investment recommendations."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=self.temperature,
                    max_tokens=1000
                )
                return response.choices[0].message.content
            
            elif self.llm_provider == "anthropic" and self.anthropic_client:
                response = await self.anthropic_client.messages.create(
                    model="claude-3-sonnet-20240229",
                    max_tokens=1000,
                    temperature=self.temperature,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                return response.content[0].text
            
            else:
                # Fallback to rule-based analysis
                return "LLM analysis unavailable - using rule-based approach."
                
        except Exception as e:
            return f"LLM analysis failed: {str(e)} - using rule-based approach."
    
    def _calculate_confidence(self, metrics: Dict[str, float], 
                            thresholds: Dict[str, tuple]) -> float:
        """
        Calculate confidence score based on how well metrics match agent criteria.
        
        Args:
            metrics: Dictionary of calculated metrics
            thresholds: Dictionary of (min, max) thresholds for each metric
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        confidence_scores = []
        
        for metric, value in metrics.items():
            if metric in thresholds:
                min_val, max_val = thresholds[metric]
                
                if min_val <= value <= max_val:
                    # Within ideal range
                    score = 1.0
                elif value < min_val:
                    # Below minimum
                    score = max(0, 1 - (min_val - value) / min_val)
                else:
                    # Above maximum
                    score = max(0, 1 - (value - max_val) / max_val)
                
                confidence_scores.append(score)
        
        return np.mean(confidence_scores) if confidence_scores else 0.5
    
    def _get_recommendation_from_score(self, score: float) -> Recommendation:
        """Convert confidence score to recommendation"""
        if score >= 0.8:
            return Recommendation.STRONG_BUY
        elif score >= 0.6:
            return Recommendation.BUY
        elif score >= 0.4:
            return Recommendation.HOLD
        elif score >= 0.2:
            return Recommendation.SELL
        else:
            return Recommendation.STRONG_SELL
    
    async def _identify_risk_factors(self, ticker: str, financial_data: Dict) -> List[str]:
        """Identify potential risk factors"""
        risk_factors = []
        
        info = financial_data.get('info', {})
        
        # Valuation risks
        pe_ratio = info.get('trailingPE', 0)
        if pe_ratio > 30:
            risk_factors.append("High P/E ratio indicates potential overvaluation")
        elif pe_ratio < 0:
            risk_factors.append("Negative earnings")
        
        # Leverage risks
        debt_to_equity = info.get('debtToEquity', 0)
        if debt_to_equity > 2.0:
            risk_factors.append("High debt-to-equity ratio")
        
        # Profitability risks
        profit_margin = info.get('profitMargins', 0)
        if profit_margin < 0:
            risk_factors.append("Negative profit margins")
        elif profit_margin < 0.05:
            risk_factors.append("Low profit margins")
        
        # Beta risk
        beta = info.get('beta', 1.0)
        if beta > 1.5:
            risk_factors.append("High beta - volatile stock")
        elif beta < 0.5:
            risk_factors.append("Very low beta - may underperform in bull markets")
        
        # Size risk
        market_cap = info.get('marketCap', 0)
        if market_cap < 2e9:  # Less than $2B
            risk_factors.append("Small-cap stock - higher volatility")
        elif market_cap > 200e9:  # More than $200B
            risk_factors.append("Large-cap stock - slower growth potential")
        
        return risk_factors
    
    async def _identify_catalysts(self, ticker: str, financial_data: Dict) -> List[str]:
        """Identify potential positive catalysts"""
        catalysts = []
        
        info = financial_data.get('info', {})
        
        # Growth catalysts
        revenue_growth = info.get('revenueGrowth', 0)
        if revenue_growth > 0.20:
            catalysts.append("Strong revenue growth")
        elif revenue_growth > 0.10:
            catalysts.append("Moderate revenue growth")
        
        # Profitability catalysts
        roe = info.get('returnOnEquity', 0)
        if roe > 0.20:
            catalysts.append("High return on equity")
        elif roe > 0.15:
            catalysts.append("Good return on equity")
        
        # Dividend catalysts
        dividend_yield = info.get('dividendYield', 0)
        if dividend_yield > 0.04:
            catalysts.append("High dividend yield")
        elif dividend_yield > 0.02:
            catalysts.append("Moderate dividend yield")
        
        # Valuation catalysts
        pe_ratio = info.get('trailingPE', 0)
        if 10 < pe_ratio < 15:
            catalysts.append("Reasonable P/E valuation")
        elif pe_ratio < 10:
            catalysts.append("Low P/E valuation")
        
        pb_ratio = info.get('priceToBook', 0)
        if 1.0 < pb_ratio < 2.0:
            catalysts.append("Reasonable price-to-book ratio")
        elif pb_ratio < 1.0:
            catalysts.append("Low price-to-book ratio")
        
        return catalysts
