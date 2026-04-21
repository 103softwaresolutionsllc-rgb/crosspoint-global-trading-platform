"""
Risk Analysis Module for QuantLib Suite
Advanced risk metrics and calculations for financial instruments
"""

import asyncio
import numpy as np
import pandas as pd
from scipy import stats
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class RiskMetrics:
    """Comprehensive risk metrics for financial instruments"""
    var_95: float
    var_99: float
    cvar_95: float
    beta: float
    correlation: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    volatility: float
    skewness: float
    kurtosis: float


class GreeksCalculator:
    """
    Options Greeks calculator with advanced methodologies.
    
    Features:
    - First and second order Greeks
    - Finite difference methods
    - Monte Carlo Greeks
    - Cross-Greeks
    - Time decay analysis
    - Volatility sensitivity
    """
    
    def __init__(self):
        self.epsilon = 1e-6  # Small change for finite differences
        
    def calculate_all_greeks(self, S: float, K: float, T: float, r: float,
                           sigma: float, option_type: str = 'call') -> Dict[str, float]:
        """
        Calculate all first and second order Greeks
        
        Args:
            S: Underlying price
            K: Strike price
            T: Time to expiration
            r: Risk-free rate
            sigma: Volatility
            option_type: 'call' or 'put'
            
        Returns:
            Dictionary with all Greeks
        """
        from .pricing import OptionPricer, OptionParams
        
        pricer = OptionPricer()
        params = OptionParams(S, K, T, r, sigma, option_type, 'european')
        
        # First order Greeks
        first_order = pricer.black_scholes(params)
        
        # Second order Greeks using finite differences
        gamma = self._calculate_gamma_finite_diff(S, K, T, r, sigma, option_type)
        
        # Cross-Greeks
        vanna = self._calculate_vanna(S, K, T, r, sigma, option_type)
        charm = self._calculate_charm(S, K, T, r, sigma, option_type)
        
        # Third order Greeks
        speed = self._calculate_speed(S, K, T, r, sigma, option_type)
        zomma = self._calculate_zomma(S, K, T, r, sigma, option_type)
        color = self._calculate_color(S, K, T, r, sigma, option_type)
        
        return {
            # First order
            'delta': first_order['delta'],
            'theta': first_order['theta'],
            'vega': first_order['vega'],
            'rho': first_order['rho'],
            
            # Second order
            'gamma': gamma,
            
            # Cross-Greeks
            'vanna': vanna,
            'charm': charm,
            
            # Third order
            'speed': speed,
            'zomma': zomma,
            'color': color,
        }
    
    def _calculate_gamma_finite_diff(self, S: float, K: float, T: float, r: float,
                                   sigma: float, option_type: str) -> float:
        """Calculate gamma using finite differences"""
        from .pricing import OptionPricer, OptionParams
        
        pricer = OptionPricer()
        
        # Delta at S + epsilon
        params_up = OptionParams(S + self.epsilon, K, T, r, sigma, option_type, 'european')
        delta_up = pricer.black_scholes(params_up)['delta']
        
        # Delta at S - epsilon
        params_down = OptionParams(S - self.epsilon, K, T, r, sigma, option_type, 'european')
        delta_down = pricer.black_scholes(params_down)['delta']
        
        # Gamma = (delta_up - delta_down) / (2 * epsilon)
        return (delta_up - delta_down) / (2 * self.epsilon)
    
    def _calculate_vanna(self, S: float, K: float, T: float, r: float,
                        sigma: float, option_type: str) -> float:
        """Calculate vanna (dDelta/dVolatility)"""
        from .pricing import OptionPricer, OptionParams
        
        pricer = OptionPricer()
        
        # Delta at sigma + epsilon
        params_up = OptionParams(S, K, T, r, sigma + self.epsilon, option_type, 'european')
        delta_up = pricer.black_scholes(params_up)['delta']
        
        # Delta at sigma - epsilon
        params_down = OptionParams(S, K, T, r, sigma - self.epsilon, option_type, 'european')
        delta_down = pricer.black_scholes(params_down)['delta']
        
        # Vanna = (delta_up - delta_down) / (2 * epsilon)
        return (delta_up - delta_down) / (2 * self.epsilon)
    
    def _calculate_charm(self, S: float, K: float, T: float, r: float,
                        sigma: float, option_type: str) -> float:
        """Calculate charm (dDelta/dTime)"""
        from .pricing import OptionPricer, OptionParams
        
        pricer = OptionPricer()
        
        # Delta at T + epsilon
        params_up = OptionParams(S, K, T + self.epsilon, r, sigma, option_type, 'european')
        delta_up = pricer.black_scholes(params_up)['delta']
        
        # Delta at T - epsilon
        params_down = OptionParams(S, K, T - self.epsilon, r, sigma, option_type, 'european')
        delta_down = pricer.black_scholes(params_down)['delta']
        
        # Charm = (delta_up - delta_down) / (2 * epsilon)
        return (delta_up - delta_down) / (2 * self.epsilon)
    
    def _calculate_speed(self, S: float, K: float, T: float, r: float,
                        sigma: float, option_type: str) -> float:
        """Calculate speed (dGamma/dSpot)"""
        gamma_up = self._calculate_gamma_finite_diff(S + self.epsilon, K, T, r, sigma, option_type)
        gamma_down = self._calculate_gamma_finite_diff(S - self.epsilon, K, T, r, sigma, option_type)
        
        # Speed = (gamma_up - gamma_down) / (2 * epsilon)
        return (gamma_up - gamma_down) / (2 * self.epsilon)
    
    def _calculate_zomma(self, S: float, K: float, T: float, r: float,
                        sigma: float, option_type: str) -> float:
        """Calculate zomma (dGamma/dVolatility)"""
        gamma_up = self._calculate_gamma_finite_diff(S, K, T, r, sigma + self.epsilon, option_type)
        gamma_down = self._calculate_gamma_finite_diff(S, K, T, r, sigma - self.epsilon, option_type)
        
        # Zomma = (gamma_up - gamma_down) / (2 * epsilon)
        return (gamma_up - gamma_down) / (2 * self.epsilon)
    
    def _calculate_color(self, S: float, K: float, T: float, r: float,
                        sigma: float, option_type: str) -> float:
        """Calculate color (dGamma/dTime)"""
        gamma_up = self._calculate_gamma_finite_diff(S, K, T + self.epsilon, r, sigma, option_type)
        gamma_down = self._calculate_gamma_finite_diff(S, K, T - self.epsilon, r, sigma, option_type)
        
        # Color = (gamma_up - gamma_down) / (2 * epsilon)
        return (gamma_up - gamma_down) / (2 * self.epsilon)


class RiskCalculator:
    """
    Comprehensive risk calculation for portfolios and individual instruments.
    
    Features:
    - Value at Risk (VaR) calculation
    - Conditional VaR (Expected Shortfall)
    - Stress testing
    - Scenario analysis
    - Correlation analysis
    - Risk contribution analysis
    """
    
    def __init__(self):
        self.confidence_levels = [0.90, 0.95, 0.99]
        
    def calculate_var(self, returns: pd.Series, method: str = 'historical',
                     confidence_level: float = 0.95) -> Dict[str, float]:
        """
        Calculate Value at Risk using multiple methods
        
        Args:
            returns: Return series
            method: 'historical', 'parametric', or 'monte_carlo'
            confidence_level: Confidence level for VaR
            
        Returns:
            Dictionary with VaR calculations
        """
        if method == 'historical':
            var = self._historical_var(returns, confidence_level)
        elif method == 'parametric':
            var = self._parametric_var(returns, confidence_level)
        elif method == 'monte_carlo':
            var = self._monte_carlo_var(returns, confidence_level)
        else:
            raise ValueError(f"Unknown VaR method: {method}")
        
        return {
            'var': var,
            'method': method,
            'confidence_level': confidence_level,
        }
    
    def _historical_var(self, returns: pd.Series, confidence_level: float) -> float:
        """Historical VaR calculation"""
        return np.percentile(returns, (1 - confidence_level) * 100)
    
    def _parametric_var(self, returns: pd.Series, confidence_level: float) -> float:
        """Parametric VaR using normal distribution"""
        mean = returns.mean()
        std = returns.std()
        
        z_score = stats.norm.ppf(1 - confidence_level)
        return mean + z_score * std
    
    def _monte_carlo_var(self, returns: pd.Series, confidence_level: float,
                        n_simulations: int = 10000) -> float:
        """Monte Carlo VaR calculation"""
        mean = returns.mean()
        std = returns.std()
        
        # Generate simulated returns
        simulated_returns = np.random.normal(mean, std, n_simulations)
        
        return np.percentile(simulated_returns, (1 - confidence_level) * 100)
    
    def calculate_cvar(self, returns: pd.Series, confidence_level: float = 0.95) -> float:
        """
        Calculate Conditional VaR (Expected Shortfall)
        
        Args:
            returns: Return series
            confidence_level: Confidence level
            
        Returns:
            Conditional VaR
        """
        var = self._historical_var(returns, confidence_level)
        
        # Average of returns that fall below VaR
        tail_losses = returns[returns <= var]
        
        if len(tail_losses) > 0:
            return tail_losses.mean()
        else:
            return var
    
    def calculate_portfolio_var(self, weights: np.ndarray, returns_matrix: pd.DataFrame,
                             confidence_level: float = 0.95) -> Dict[str, Any]:
        """
        Calculate portfolio VaR with component contributions
        
        Args:
            weights: Portfolio weights
            returns_matrix: Matrix of asset returns
            confidence_level: Confidence level
            
        Returns:
            Dictionary with portfolio VaR and contributions
        """
        # Calculate portfolio returns
        portfolio_returns = (returns_matrix * weights).sum(axis=1)
        
        # Portfolio VaR
        portfolio_var = self._historical_var(portfolio_returns, confidence_level)
        
        # Component VaR (simplified)
        component_vars = []
        for i, weight in enumerate(weights):
            asset_returns = returns_matrix.iloc[:, i]
            
            # Marginal VaR approximation
            correlation = portfolio_returns.corr(asset_returns)
            asset_var = self._historical_var(asset_returns, confidence_level)
            
            component_var = weight * correlation * asset_var
            component_vars.append(component_var)
        
        # Normalize component VaRs
        total_component_var = sum(component_vars)
        if total_component_var != 0:
            component_vars = [cv / total_component_var * portfolio_var for cv in component_vars]
        
        return {
            'portfolio_var': portfolio_var,
            'component_vars': component_vars,
            'diversification_benefit': portfolio_var - sum(component_vars),
            'weights': weights.tolist(),
        }
    
    def stress_test(self, portfolio_value: float, returns: pd.Series,
                   scenarios: Dict[str, float]) -> Dict[str, Any]:
        """
        Perform stress testing on portfolio
        
        Args:
            portfolio_value: Current portfolio value
            returns: Historical returns
            scenarios: Dictionary of stress scenarios
            
        Returns:
            Dictionary with stress test results
        """
        results = {}
        
        for scenario_name, shock_magnitude in scenarios.items():
            # Apply shock to returns
            shocked_returns = returns + shock_magnitude
            
            # Calculate stressed VaR
            stressed_var = self._historical_var(shocked_returns, 0.95)
            
            # Calculate portfolio loss
            portfolio_loss = portfolio_value * abs(stressed_var)
            
            results[scenario_name] = {
                'shock_magnitude': shock_magnitude,
                'stressed_var': stressed_var,
                'portfolio_loss': portfolio_loss,
                'loss_percentage': (portfolio_loss / portfolio_value) * 100,
            }
        
        return results
    
    def calculate_correlation_matrix(self, returns_matrix: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate correlation matrix for assets
        
        Args:
            returns_matrix: Matrix of asset returns
            
        Returns:
            Correlation matrix
        """
        return returns_matrix.corr()
    
    def calculate_beta(self, asset_returns: pd.Series, market_returns: pd.Series) -> float:
        """
        Calculate beta of an asset relative to market
        
        Args:
            asset_returns: Asset returns
            market_returns: Market returns
            
        Returns:
            Beta coefficient
        """
        # Align the series
        aligned_data = pd.concat([asset_returns, market_returns], axis=1).dropna()
        
        if len(aligned_data) < 30:
            return 1.0  # Default beta
        
        asset = aligned_data.iloc[:, 0]
        market = aligned_data.iloc[:, 1]
        
        # Calculate beta using linear regression
        covariance = np.cov(asset, market)[0, 1]
        market_variance = np.var(market)
        
        return covariance / market_variance if market_variance != 0 else 1.0
    
    def calculate_drawdowns(self, returns: pd.Series) -> Dict[str, float]:
        """
        Calculate drawdown statistics
        
        Args:
            returns: Return series
            
        Returns:
            Dictionary with drawdown metrics
        """
        cumulative = np.cumprod(1 + returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max
        
        max_drawdown = np.min(drawdown)
        max_drawdown_duration = self._calculate_max_drawdown_duration(drawdown)
        
        return {
            'max_drawdown': max_drawdown,
            'max_drawdown_duration': max_drawdown_duration,
            'current_drawdown': drawdown.iloc[-1],
            'average_drawdown': np.mean(drawdown[drawdown < 0]),
        }
    
    def _calculate_max_drawdown_duration(self, drawdown: pd.Series) -> int:
        """Calculate maximum drawdown duration in days"""
        is_drawdown = drawdown < 0
        
        if not is_drawdown.any():
            return 0
        
        # Find consecutive drawdown periods
        durations = []
        current_duration = 0
        
        for dd in is_drawdown:
            if dd:
                current_duration += 1
            else:
                if current_duration > 0:
                    durations.append(current_duration)
                current_duration = 0
        
        # Add the last duration if we're still in drawdown
        if current_duration > 0:
            durations.append(current_duration)
        
        return max(durations) if durations else 0
    
    def calculate_risk_adjusted_returns(self, returns: pd.Series,
                                       risk_free_rate: float = 0.02) -> Dict[str, float]:
        """
        Calculate risk-adjusted return metrics
        
        Args:
            returns: Return series
            risk_free_rate: Annual risk-free rate
            
        Returns:
            Dictionary with risk-adjusted metrics
        """
        # Annualize returns
        annual_return = (1 + returns.mean()) ** 252 - 1
        annual_volatility = returns.std() * np.sqrt(252)
        
        # Sharpe ratio
        sharpe_ratio = (annual_return - risk_free_rate) / annual_volatility if annual_volatility > 0 else 0
        
        # Sortino ratio
        downside_returns = returns[returns < 0]
        downside_volatility = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else 0
        sortino_ratio = (annual_return - risk_free_rate) / downside_volatility if downside_volatility > 0 else 0
        
        # Information ratio (requires benchmark)
        info_ratio = 0  # Placeholder
        
        # Calmar ratio
        max_drawdown = self.calculate_drawdowns(returns)['max_drawdown']
        calmar_ratio = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0
        
        return {
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'information_ratio': info_ratio,
            'calmar_ratio': calmar_ratio,
            'annual_return': annual_return,
            'annual_volatility': annual_volatility,
        }
    
    def scenario_analysis(self, portfolio_value: float, weights: np.ndarray,
                         returns_matrix: pd.DataFrame, scenarios: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
        """
        Perform scenario analysis on portfolio
        
        Args:
            portfolio_value: Current portfolio value
            weights: Portfolio weights
            returns_matrix: Historical returns
            scenarios: Dictionary of scenarios with asset shocks
            
        Returns:
            Dictionary with scenario analysis results
        """
        results = {}
        
        for scenario_name, shocks in scenarios.items():
            # Apply scenario shocks to asset returns
            shocked_returns = returns_matrix.copy()
            
            for asset_name, shock in shocks.items():
                if asset_name in shocked_returns.columns:
                    shocked_returns[asset_name] += shock
            
            # Calculate portfolio returns under scenario
            scenario_portfolio_returns = (shocked_returns * weights).sum(axis=1)
            
            # Calculate scenario metrics
            scenario_return = scenario_portfolio_returns.mean()
            scenario_volatility = scenario_portfolio_returns.std()
            scenario_var = self._historical_var(scenario_portfolio_returns, 0.95)
            
            # Calculate portfolio value change
            portfolio_change = portfolio_value * scenario_return
            
            results[scenario_name] = {
                'scenario_return': scenario_return,
                'scenario_volatility': scenario_volatility,
                'scenario_var': scenario_var,
                'portfolio_change': portfolio_change,
                'portfolio_change_percentage': (portfolio_change / portfolio_value) * 100,
                'shocks': shocks,
            }
        
        return results
