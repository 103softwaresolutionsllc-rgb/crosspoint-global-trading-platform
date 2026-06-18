"""
Jim Simons Quantitative Agent
Based on quantitative, mathematical, and algorithmic trading principles:
- Trend following & Momentum
- Mean reversion & Overbought/Oversold indicators
- Statistical volatility regime detection
- Technical indicator alignment (RSI, MACD, Moving Averages, Bollinger Bands)
"""

import asyncio
from typing import Dict, Any, List
import numpy as np
import pandas as pd

from ..base import BaseAgent, AgentResult, AgentType, Recommendation
from ..macro_context import apply_macro_to_result, resolve_macro


class SimonsAgent(BaseAgent):
    """
    Jim Simons AI Agent implementing a quantitative, mathematical approach to trading:
    
    Core Principles:
    1. Trend Following: Trade in the direction of the medium-to-long term trend.
    2. Mean Reversion: Capitalize on short-term overextensions.
    3. Mathematical Rigor: Rely entirely on price, volume, and volatility signals rather than fundamentals.
    4. Volatility regime detection: Dynamically damp or scale confidence based on variance ratios.
    """
    
    def __init__(self):
        super().__init__("Jim Simons", AgentType.QUANT_AGENT)
        
        # Quant thresholds
        self.thresholds = {
            'rsi': (30.0, 70.0),       # RSI neutral boundaries
            'bb_position': (0.1, 0.9),  # Bollinger Band boundaries
        }
        
    async def analyze(self, ticker: str, **kwargs) -> AgentResult:
        """Analyze a stock using quantitative and technical indicators"""
        try:
            macro = await resolve_macro(kwargs)
            # Get financial data (which includes history)
            financial_data = await self._get_financial_data(ticker)
            price_data = financial_data.get('price_data')
            
            if price_data is None or price_data.empty:
                raise ValueError(f"No price data available for {ticker}")
                
            # Calculate technical indicators
            indicators = await self._calculate_technical_indicators(price_data)
            
            # Run structural regime check (inherited from BaseAgent)
            regime = await self._structural_regime_check(ticker, price_data)
            
            # Calculate Quant Sub-Scores
            momentum_score = self._calculate_momentum_score(indicators)
            reversion_score = self._calculate_reversion_score(indicators)
            volatility_score = regime.get('dampening', 1.0)
            
            # Calculate overall conviction (score from 0.0 to 1.0)
            # Weights: 50% Momentum/Trend, 30% Mean Reversion, 20% Volatility stability
            overall_score = (0.5 * momentum_score) + (0.3 * reversion_score) + (0.2 * volatility_score)
            
            # Determine recommendation
            recommendation = self._get_quant_recommendation(indicators, momentum_score, reversion_score, volatility_score)
            
            # Confidence is scaled by the structural volatility dampening
            confidence = float(np.clip(overall_score * volatility_score, 0.0, 1.0))
            
            # Generate quantitative reasoning
            reasoning = self._generate_quant_reasoning(ticker, indicators, regime, momentum_score, reversion_score)
            
            # Risks and Catalysts
            risk_factors = self._identify_quant_risks(indicators, regime)
            catalysts = self._identify_quant_catalysts(indicators, regime)
            
            # Establish price target (using 30-day Bollinger upper/lower as near-term target based on side)
            price_target = self._estimate_price_target(indicators, recommendation)
            
            result = AgentResult(
                agent_name=self.name,
                ticker=ticker.upper(),
                recommendation=recommendation,
                confidence=confidence,
                reasoning=reasoning,
                key_metrics={
                    'rsi': indicators.get('rsi', 50.0),
                    'macd': indicators.get('macd', 0.0),
                    'bb_position': indicators.get('bb_position', 0.5),
                    'momentum_score': momentum_score,
                    'reversion_score': reversion_score,
                    'volatility_dampening': volatility_score,
                    'z_score': regime.get('z_score', 0.0),
                    'vol_ratio': regime.get('vol_ratio', 1.0)
                },
                risk_factors=risk_factors,
                catalysts=catalysts,
                price_target=price_target,
                time_horizon="1-3 months",
                additional_data={
                    'investment_style': 'Quantitative Systematic',
                    'holding_period': 'Short to Medium-term',
                    'regime_volatility': 'High' if volatility_score < 0.8 else 'Normal',
                }
            )
            
            return apply_macro_to_result(result, macro, "simons")
            
        except Exception as e:
            return AgentResult(
                agent_name=self.name,
                ticker=ticker.upper(),
                recommendation=Recommendation.HOLD,
                confidence=0.0,
                reasoning=f"Quantitative analysis failed: {str(e)}",
                key_metrics={},
                risk_factors=["Analysis error"],
                catalysts=[]
            )
            
    def _calculate_momentum_score(self, indicators: Dict[str, Any]) -> float:
        """Score trend and momentum on a 0-1 scale"""
        score = 0.0
        
        # 1. Price vs MAs
        if indicators.get('price_above_ma_50', False):
            score += 0.25
        if indicators.get('price_above_ma_200', False):
            score += 0.25
        if indicators.get('ma_50_above_ma_200', False):
            score += 0.25
            
        # 2. MACD alignment
        if indicators.get('macd_bullish', False):
            score += 0.25
            
        return score
        
    def _calculate_reversion_score(self, indicators: Dict[str, Any]) -> float:
        """Score mean reversion / oversold opportunities on a 0-1 scale"""
        rsi = indicators.get('rsi', 50.0)
        bb_pos = indicators.get('bb_position', 0.5)
        
        # We look for healthy range vs extreme oversold/overbought states
        # 0.5 is baseline. Overbought/oversold gives skew.
        score = 0.5
        
        # Oversold setup (potential reversal candidate)
        if rsi < 35:
            score += 0.3
        elif rsi < 45:
            score += 0.15
            
        # Bollinger lower bound stabilization
        if bb_pos < 0.15:
            score += 0.2
        elif bb_pos < 0.3:
            score += 0.1
            
        # Overbought penalty
        if rsi > 70:
            score -= 0.3
        elif rsi > 60:
            score -= 0.1
            
        if bb_pos > 0.85:
            score -= 0.2
            
        return float(np.clip(score, 0.0, 1.0))
        
    def _get_quant_recommendation(self, indicators: Dict[str, Any], momentum: float, reversion: float, volatility: float) -> Recommendation:
        """Determine recommendation based on technical and statistical scores"""
        rsi = indicators.get('rsi', 50.0)
        bb_pos = indicators.get('bb_position', 0.5)
        macd_bullish = indicators.get('macd_bullish', False)
        
        # Trend is strongly bullish and not extremely overextended
        if momentum >= 0.75 and rsi <= 68 and bb_pos <= 0.9:
            return Recommendation.STRONG_BUY
            
        # Trend is positive or oversold bounce is starting
        if (momentum >= 0.5 and rsi <= 65) or (rsi < 30 and bb_pos < 0.1):
            return Recommendation.BUY
            
        # Strong downward trend and overbought or breaking lower Bollinger Band
        if momentum <= 0.25 and (rsi >= 65 or bb_pos >= 0.9):
            return Recommendation.STRONG_SELL
            
        # Downward momentum
        if momentum <= 0.25 or (rsi > 70 and bb_pos > 0.95):
            return Recommendation.SELL
            
        return Recommendation.HOLD
        
    def _generate_quant_reasoning(self, ticker: str, indicators: Dict[str, Any], regime: Dict[str, float], momentum: float, reversion: float) -> str:
        """Create structured quantitative analysis explanation"""
        rsi = indicators.get('rsi', 50.0)
        bb_pos = indicators.get('bb_position', 0.5)
        current_price = indicators.get('current_price', 0.0)
        
        parts = []
        
        # Trend assessment
        if momentum >= 0.75:
            parts.append(f"{ticker} exhibits a strong bullish trend with price above major moving averages and a bullish MACD cross.")
        elif momentum >= 0.5:
            parts.append(f"{ticker} shows moderate upward trend characteristics.")
        elif momentum <= 0.25:
            parts.append(f"{ticker} displays bearish technical structures with price trading below the 50-day and 200-day moving averages.")
        else:
            parts.append(f"{ticker} is in a neutral or consolidation range.")
            
        # Indicator states
        parts.append(f"RSI is currently at {rsi:.1f} and the asset is trading at {bb_pos*100:.1f}% of its Bollinger Band width.")
        
        # Volatility regime
        vol_ratio = regime.get('vol_ratio', 1.0)
        z_score = regime.get('z_score', 0.0)
        if vol_ratio > 2.0 or abs(z_score) > 2.5:
            parts.append(f"Statistical check indicates an elevated volatility regime (vol ratio: {vol_ratio:.2f}, z-score: {z_score:.2f}), suggesting increased variance.")
        else:
            parts.append("Volatility and volume metrics indicate a stable structural regime.")
            
        return " ".join(parts)
        
    def _identify_quant_risks(self, indicators: Dict[str, Any], regime: Dict[str, float]) -> List[str]:
        """Identify key technical/statistical risks"""
        risks = []
        rsi = indicators.get('rsi', 50.0)
        bb_pos = indicators.get('bb_position', 0.5)
        vol_ratio = regime.get('vol_ratio', 1.0)
        
        if rsi > 70:
            risks.append("Asset is technically overbought (RSI > 70)")
        if bb_pos > 0.95:
            risks.append("Price is testing upper Bollinger Band limit")
        if not indicators.get('price_above_ma_200', True):
            risks.append("Price is in a long-term downtrend (below 200 MA)")
        if vol_ratio > 2.0:
            risks.append(f"High volatility regime detected (Short-term/Long-term vol: {vol_ratio:.1f})")
            
        return risks
        
    def _identify_quant_catalysts(self, indicators: Dict[str, Any], regime: Dict[str, float]) -> List[str]:
        """Identify key technical catalysts"""
        catalysts = []
        rsi = indicators.get('rsi', 50.0)
        bb_pos = indicators.get('bb_position', 0.5)
        
        if indicators.get('ma_50_above_ma_200', False) and indicators.get('price_above_ma_50', False):
            catalysts.append("Bullish Golden Cross active")
        if indicators.get('macd_bullish', False):
            catalysts.append("Bullish MACD histogram expansion")
        if rsi < 30:
            catalysts.append("Oversold technical condition (RSI < 30) supportive of mean reversion")
        if bb_pos < 0.05:
            catalysts.append("Price testing lower Bollinger Band boundary, indicating potential bounce")
            
        return catalysts
        
    def _estimate_price_target(self, indicators: Dict[str, Any], recommendation: Recommendation) -> float:
        """Estimate near-term target using Bollinger Bands and Moving Averages"""
        current_price = indicators.get('current_price', 0.0)
        bb_upper = indicators.get('bb_upper', current_price * 1.05)
        bb_lower = indicators.get('bb_lower', current_price * 0.95)
        ma_50 = indicators.get('ma_50', current_price)
        
        if recommendation in (Recommendation.STRONG_BUY, Recommendation.BUY):
            # Target upper Bollinger Band or 5% above price
            return float(max(bb_upper, current_price * 1.05))
        elif recommendation in (Recommendation.STRONG_SELL, Recommendation.SELL):
            # Target lower Bollinger Band or 5% below price
            return float(min(bb_lower, current_price * 0.95))
        else:
            # Target middle of range (50 MA or Bollinger middle)
            return float(ma_50)
