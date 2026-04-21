"""
Discounted Cash Flow (DCF) Analysis Module
CFA Level II/III valuation methodology
"""

import asyncio
import numpy as np
import pandas as pd
import yfinance as yf
from dataclasses import dataclass
from typing import Optional, Tuple
from scipy.optimize import minimize_scalar


@dataclass
class DCFResult:
    """Results from DCF analysis"""
    ticker: str
    valuation: float
    fair_value: float
    upside: float
    wacc: float
    terminal_growth_rate: float
    fcf_projections: np.ndarray
    present_values: np.ndarray
    analysis_date: pd.Timestamp


class DCFModel:
    """
    Discounted Cash Flow valuation model implementing CFA curriculum standards.
    
    Features:
    - Free Cash Flow to Firm (FCFF) projection
    - WACC calculation with CAPM
    - Terminal value calculation
    - Sensitivity analysis
    - Multiple growth scenarios
    """
    
    def __init__(self):
        self.risk_free_rate = 0.0425  # 10-year Treasury yield
        self.equity_risk_premium = 0.055  # Historical market premium
        self.default_beta = 1.0
        self.default_terminal_growth = 0.025  # 2.5% long-term GDP growth
        self.projection_years = 5
        
    async def analyze(self, ticker: str, 
                     custom_wacc: Optional[float] = None,
                     custom_growth_rate: Optional[float] = None,
                     projection_years: int = 5) -> DCFResult:
        """
        Perform comprehensive DCF analysis
        
        Args:
            ticker: Stock ticker symbol
            custom_wacc: Override calculated WACC
            custom_growth_rate: Override terminal growth rate
            projection_years: Number of years to project FCF
            
        Returns:
            DCFResult with comprehensive valuation metrics
        """
        try:
            # Get financial data
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Calculate WACC
            if custom_wacc:
                wacc = custom_wacc
            else:
                wacc = await self._calculate_wacc(stock, info)
            
            # Project free cash flows
            fcf_projections = await self._project_fcf(stock, projection_years)
            
            # Calculate terminal value
            terminal_growth = custom_growth_rate or self.default_terminal_growth
            terminal_value = self._calculate_terminal_value(
                fcf_projections[-1], wacc, terminal_growth
            )
            
            # Calculate present values
            present_values = self._discount_cash_flows(
                fcf_projections, terminal_value, wacc
            )
            
            # Calculate enterprise value and equity value
            enterprise_value = np.sum(present_values)
            equity_value = await self._calculate_equity_value(
                enterprise_value, stock, info
            )
            
            # Calculate fair value per share
            shares_outstanding = info.get('sharesOutstanding', 1)
            fair_value = equity_value / shares_outstanding
            
            # Calculate upside/downside
            current_price = info.get('currentPrice', 0)
            upside = (fair_value - current_price) / current_price if current_price > 0 else 0
            
            return DCFResult(
                ticker=ticker.upper(),
                valuation=enterprise_value,
                fair_value=fair_value,
                upside=upside,
                wacc=wacc,
                terminal_growth_rate=terminal_growth,
                fcf_projections=fcf_projections,
                present_values=present_values,
                analysis_date=pd.Timestamp.now()
            )
            
        except Exception as e:
            raise ValueError(f"DCF analysis failed for {ticker}: {str(e)}")
    
    async def _calculate_wacc(self, stock: yf.Ticker, info: dict) -> float:
        """Calculate Weighted Average Cost of Capital"""
        try:
            # Get market cap and debt
            market_cap = info.get('marketCap', 0)
            total_debt = info.get('totalDebt', 0)
            enterprise_value = market_cap + total_debt
            
            # Calculate cost of equity using CAPM
            beta = info.get('beta', self.default_beta)
            cost_of_equity = (self.risk_free_rate + 
                             beta * self.equity_risk_premium)
            
            # Calculate cost of debt
            interest_expense = info.get('interestExpense', 0)
            ebit = info.get('ebitda', 0) - info.get('depreciation', 0)
            cost_of_debt = interest_expense / total_debt if total_debt > 0 else 0.06
            
            # Calculate weights
            equity_weight = market_cap / enterprise_value if enterprise_value > 0 else 0.7
            debt_weight = total_debt / enterprise_value if enterprise_value > 0 else 0.3
            
            # Assume 21% corporate tax rate
            tax_rate = 0.21
            
            # Calculate WACC
            wacc = (equity_weight * cost_of_equity + 
                   debt_weight * cost_of_debt * (1 - tax_rate))
            
            return max(wacc, 0.05)  # Minimum 5% WACC
            
        except Exception:
            return 0.10  # Default 10% WACC
    
    async def _project_fcf(self, stock: yf.Ticker, years: int) -> np.ndarray:
        """Project future free cash flows"""
        try:
            # Get historical financials
            financials = stock.financials
            cash_flow = stock.cashflow
            
            # Calculate historical FCF
            fcf_history = []
            for year in cash_flow.columns:
                operating_cf = cash_flow.loc['Total Cash From Operating Activities', year]
                capex = cash_flow.loc['Capital Expenditures', year]
                fcf = operating_cf - capex
                fcf_history.append(fcf)
            
            if not fcf_history:
                # Default FCF based on revenue and margins
                revenue = financials.loc['Total Revenue', financials.columns[0]]
                fcf_margin = 0.10  # 10% FCF margin
                fcf_history = [revenue * fcf_margin] * 3
            
            # Calculate growth rates
            fcf_array = np.array(fcf_history)
            growth_rates = []
            
            for i in range(1, len(fcf_array)):
                if fcf_array[i-1] > 0:
                    growth_rate = (fcf_array[i] - fcf_array[i-1]) / fcf_array[i-1]
                    growth_rates.append(growth_rate)
            
            # Use average historical growth, but cap at reasonable levels
            avg_growth = np.mean(growth_rates) if growth_rates else 0.05
            avg_growth = max(min(avg_growth, 0.20), -0.10)  # Cap between -10% and 20%
            
            # Project future FCF with declining growth
            projections = []
            base_fcf = fcf_array[-1]
            
            for year in range(years):
                # Growth rate declines each year towards terminal growth
                year_growth = avg_growth * (1 - year / years) + self.default_terminal_growth * (year / years)
                projected_fcf = base_fcf * (1 + year_growth)
                projections.append(projected_fcf)
                base_fcf = projected_fcf
            
            return np.array(projections)
            
        except Exception:
            # Default projections
            base_fcf = 1000000000  # $1B default
            return np.array([base_fcf * (1 + 0.05)**i for i in range(years)])
    
    def _calculate_terminal_value(self, final_fcf: float, wacc: float, 
                                 growth_rate: float) -> float:
        """Calculate terminal value using Gordon Growth Model"""
        if wacc <= growth_rate:
            # Avoid division by negative or very small numbers
            growth_rate = wacc - 0.01
        
        return final_fcf * (1 + growth_rate) / (wacc - growth_rate)
    
    def _discount_cash_flows(self, fcf_projections: np.ndarray, 
                           terminal_value: float, wacc: float) -> np.ndarray:
        """Discount cash flows to present value"""
        present_values = []
        
        for i, fcf in enumerate(fcf_projections):
            pv = fcf / ((1 + wacc) ** (i + 1))
            present_values.append(pv)
        
        # Discount terminal value
        terminal_pv = terminal_value / ((1 + wacc) ** len(fcf_projections))
        present_values.append(terminal_pv)
        
        return np.array(present_values)
    
    async def _calculate_equity_value(self, enterprise_value: float, 
                                    stock: yf.Ticker, info: dict) -> float:
        """Calculate equity value from enterprise value"""
        try:
            # Subtract debt and add cash
            total_debt = info.get('totalDebt', 0)
            cash = info.get('totalCash', 0)
            
            equity_value = enterprise_value - total_debt + cash
            return max(equity_value, 0)
            
        except Exception:
            return enterprise_value * 0.7  # Assume 70% equity portion
    
    async def sensitivity_analysis(self, ticker: str) -> dict:
        """Perform sensitivity analysis on WACC and growth rates"""
        base_result = await self.analyze(ticker)
        
        scenarios = {}
        
        # WACC sensitivity
        wacc_range = [base_result.wacc * (1 + x) for x in [-0.2, -0.1, 0, 0.1, 0.2]]
        for wacc in wacc_range:
            result = await self.analyze(ticker, custom_wacc=wacc)
            scenarios[f'WACC_{wacc:.3f}'] = result.fair_value
        
        # Growth rate sensitivity
        growth_range = [0.015, 0.020, 0.025, 0.030, 0.035]
        for growth in growth_range:
            result = await self.analyze(ticker, custom_growth_rate=growth)
            scenarios[f'Growth_{growth:.3f}'] = result.fair_value
        
        return scenarios
    
    async def monte_carlo_simulation(self, ticker: str, iterations: int = 1000) -> dict:
        """Monte Carlo simulation for valuation uncertainty"""
        valuations = []
        
        base_result = await self.analyze(ticker)
        
        for _ in range(iterations):
            # Random WACC (±20%)
            wacc_variation = np.random.normal(0, 0.02)
            wacc = base_result.wacc + wacc_variation
            
            # Random growth rate (±1%)
            growth_variation = np.random.normal(0, 0.005)
            growth_rate = base_result.terminal_growth_rate + growth_variation
            
            try:
                result = await self.analyze(ticker, custom_wacc=wacc, 
                                          custom_growth_rate=growth_rate)
                valuations.append(result.fair_value)
            except:
                continue
        
        if valuations:
            return {
                'mean': np.mean(valuations),
                'std': np.std(valuations),
                'min': np.min(valuations),
                'max': np.max(valuations),
                'percentiles': {
                    '5th': np.percentile(valuations, 5),
                    '25th': np.percentile(valuations, 25),
                    '50th': np.percentile(valuations, 50),
                    '75th': np.percentile(valuations, 75),
                    '95th': np.percentile(valuations, 95)
                }
            }
        
        return {}
