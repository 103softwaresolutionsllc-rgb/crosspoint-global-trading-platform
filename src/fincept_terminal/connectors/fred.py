"""
FRED (Federal Reserve Economic Data) Connector
Provides access to thousands of economic time series from the Federal Reserve
"""

import asyncio
import aiohttp
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import json


@dataclass
class FREDSeries:
    """Data structure for FRED economic series"""
    series_id: str
    title: str
    units: str
    frequency: str
    data: pd.DataFrame
    last_updated: datetime


class FREDConnector:
    """
    FRED data connector for economic data and indicators.
    
    Features:
    - GDP and economic growth data
    - Employment and labor market indicators
    - Inflation and price indices
    - Interest rates and monetary policy
    - Housing market data
    - Consumer confidence and sentiment
    - International economic data
    - Real-time economic releases
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or "YOUR_FRED_API_KEY"  # User should provide their own
        self.base_url = "https://api.stlouisfed.org/fred"
        self.session = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def get_data(self, series_id: str, start_date: Optional[str] = None,
                      end_date: Optional[str] = None) -> pd.DataFrame:
        """
        Get economic data for a specific series
        
        Args:
            series_id: FRED series ID (e.g., 'GDP', 'UNRATE', 'CPIAUCSL')
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            DataFrame with date and value columns
        """
        try:
            # Build URL
            params = {
                'series_id': series_id,
                'api_key': self.api_key,
                'file_type': 'json',
                'observation_start': start_date or '1900-01-01',
                'observation_end': end_date or datetime.now().strftime('%Y-%m-%d'),
            }
            
            url = f"{self.base_url}/series/observations"
            
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    raise ValueError(f"FRED API error: {response.status}")
                
                data = await response.json()
            
            if 'observations' not in data:
                raise ValueError(f"No data found for series {series_id}")
            
            # Convert to DataFrame
            observations = data['observations']
            df = pd.DataFrame(observations)
            
            # Convert date column and set as index
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            
            # Convert values to numeric
            df['value'] = pd.to_numeric(df['value'], errors='coerce')
            
            # Drop missing values
            df = df.dropna(subset=['value'])
            
            return df[['value']]
            
        except Exception as e:
            raise ValueError(f"Failed to get FRED data for {series_id}: {str(e)}")
    
    async def get_series_info(self, series_id: str) -> Dict[str, Any]:
        """
        Get metadata for a FRED series
        
        Args:
            series_id: FRED series ID
            
        Returns:
            Dictionary with series information
        """
        try:
            params = {
                'series_id': series_id,
                'api_key': self.api_key,
                'file_type': 'json',
            }
            
            url = f"{self.base_url}/series"
            
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    raise ValueError(f"FRED API error: {response.status}")
                
                data = await response.json()
            
            if 'seriess' not in data or len(data['seriess']) == 0:
                raise ValueError(f"No series found for {series_id}")
            
            return data['seriess'][0]
            
        except Exception as e:
            raise ValueError(f"Failed to get series info for {series_id}: {str(e)}")
    
    async def get_multiple_series(self, series_ids: List[str]) -> Dict[str, pd.DataFrame]:
        """
        Get data for multiple series simultaneously
        
        Args:
            series_ids: List of FRED series IDs
            
        Returns:
            Dictionary with DataFrames for each series
        """
        results = {}
        
        for series_id in series_ids:
            try:
                data = await self.get_data(series_id)
                results[series_id] = data
            except Exception as e:
                results[series_id] = pd.DataFrame()  # Empty DataFrame on error
        
        return results
    
    async def search_series(self, search_text: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Search for FRED series by text
        
        Args:
            search_text: Text to search for
            limit: Maximum number of results
            
        Returns:
            List of matching series
        """
        try:
            params = {
                'search_text': search_text,
                'api_key': self.api_key,
                'file_type': 'json',
                'limit': limit,
            }
            
            url = f"{self.base_url}/series/search"
            
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    raise ValueError(f"FRED API error: {response.status}")
                
                data = await response.json()
            
            return data.get('seriess', [])
            
        except Exception as e:
            raise ValueError(f"Failed to search FRED series: {str(e)}")
    
    async def get_gdp_data(self, real: bool = True, annual: bool = True) -> pd.DataFrame:
        """
        Get GDP data
        
        Args:
            real: True for real GDP, False for nominal GDP
            annual: True for annual data, False for quarterly
            
        Returns:
            DataFrame with GDP data
        """
        if real:
            series_id = 'GDPC1' if annual else 'GDPC1'
        else:
            series_id = 'GDP' if annual else 'GDP'
        
        return await self.get_data(series_id)
    
    async def get_inflation_data(self, cpi_type: str = 'CPIAUCSL') -> pd.DataFrame:
        """
        Get inflation data
        
        Args:
            cpi_type: Type of CPI data
                'CPIAUCSL' - Consumer Price Index for All Urban Consumers
                'CPILFESL' - Core CPI (excluding food and energy)
                'PCEPI' - Personal Consumption Expenditures Price Index
                
        Returns:
            DataFrame with inflation data
        """
        return await self.get_data(cpi_type)
    
    async def get_employment_data(self) -> Dict[str, pd.DataFrame]:
        """
        Get comprehensive employment data
        
        Returns:
            Dictionary with various employment indicators
        """
        employment_series = [
            'UNRATE',      # Unemployment Rate
            'PAYEMS',      # All Employees: Total Nonfarm Payrolls
            'CIVPART',     # Labor Force Participation Rate
            'EMRATIO',     # Employment-Population Ratio
            'ICSA',        # Initial Claims
            'CCSA',        # Continued Claims
        ]
        
        return await self.get_multiple_series(employment_series)
    
    async def get_interest_rates(self) -> Dict[str, pd.DataFrame]:
        """
        Get interest rate data
        
        Returns:
            Dictionary with various interest rates
        """
        rate_series = [
            'FEDFUNDS',    # Federal Funds Rate
            'DGS10',       # 10-Year Treasury Constant Maturity Rate
            'DGS2',        # 2-Year Treasury Constant Maturity Rate
            'DGS30',       # 30-Year Treasury Constant Maturity Rate
            'DGS5',        # 5-Year Treasury Constant Maturity Rate
            'MORTGAGE30US', # 30-Year Fixed Rate Mortgage Average
        ]
        
        return await self.get_multiple_series(rate_series)
    
    async def get_housing_data(self) -> Dict[str, pd.DataFrame]:
        """
        Get housing market data
        
        Returns:
            Dictionary with housing indicators
        """
        housing_series = [
            'HOUST',       # Housing Starts: Total
            'MSPUS',       # Median Sales Price of Houses Sold
            'PERMIT',      # New Private Housing Units Authorized by Building Permits
            'CSUSHPISA',   # S&P/Case-Shiller U.S. National Home Price Index
            'MORTGAGE30US', # 30-Year Fixed Rate Mortgage Average
            'EVACANTUSQ176N', # Rental Vacancy Rate for the United States
        ]
        
        return await self.get_multiple_series(housing_series)
    
    async def get_consumer_data(self) -> Dict[str, pd.DataFrame]:
        """
        Get consumer confidence and spending data
        
        Returns:
            Dictionary with consumer indicators
        """
        consumer_series = [
            'UMCSENT',     # University of Michigan Consumer Sentiment
            'CCI',         # Consumer Confidence Index
            'PCE',         # Personal Consumption Expenditures
            'DSPIC96',     # Real Personal Consumption Expenditures
            'MEHOINUSA672N', # Median Household Income
            'PSAVERT',     # Personal Saving Rate
        ]
        
        return await self.get_multiple_series(consumer_series)
    
    async def get_monetary_data(self) -> Dict[str, pd.DataFrame]:
        """
        Get monetary aggregates and banking data
        
        Returns:
            Dictionary with monetary indicators
        """
        monetary_series = [
            'M2SL',        # M2 Money Supply
            'M1SL',        # M1 Money Supply
            'BOGMBASE',     # Monetary Base
            'TOTCI',        # Commercial and Industrial Loans
            'DPSACBW027SBOG', # Deposits, All Commercial Banks
            'WALCL',        # Assets: Total Assets: Total Assets (Less Eliminations from Consolidation): Wednesday Level
        ]
        
        return await self.get_multiple_series(monetary_series)
    
    async def get_international_data(self, country_codes: List[str] = None) -> Dict[str, pd.DataFrame]:
        """
        Get international economic data
        
        Args:
            country_codes: List of country codes (e.g., ['JP', 'DE', 'GB'])
            
        Returns:
            Dictionary with international data
        """
        if country_codes is None:
            country_codes = ['JP', 'DE', 'GB', 'CN', 'CA']
        
        international_series = []
        
        for code in country_codes:
            international_series.extend([
                f'{code}NGDP',     # Nominal GDP
                f'{code}RGDP',     # Real GDP
                f'{code}CPIALL',   # Consumer Price Index
                f'{code}IR3TIB01M', # 3-Month Interbank Rate
            ])
        
        return await self.get_multiple_series(international_series)
    
    async def get_releases(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get recent economic releases
        
        Args:
            limit: Maximum number of releases
            
        Returns:
            List of recent releases
        """
        try:
            params = {
                'api_key': self.api_key,
                'file_type': 'json',
                'limit': limit,
            }
            
            url = f"{self.base_url}/releases"
            
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    raise ValueError(f"FRED API error: {response.status}")
                
                data = await response.json()
            
            return data.get('releases', [])
            
        except Exception as e:
            raise ValueError(f"Failed to get releases: {str(e)}")
    
    async def get_release_dates(self, release_id: int) -> List[Dict[str, Any]]:
        """
        Get release dates for a specific economic release
        
        Args:
            release_id: FRED release ID
            
        Returns:
            List of release dates
        """
        try:
            params = {
                'release_id': release_id,
                'api_key': self.api_key,
                'file_type': 'json',
            }
            
            url = f"{self.base_url}/release/dates"
            
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    raise ValueError(f"FRED API error: {response.status}")
                
                data = await response.json()
            
            return data.get('release_dates', [])
            
        except Exception as e:
            raise ValueError(f"Failed to get release dates: {str(e)}")
    
    async def get_economic_dashboard(self) -> Dict[str, Any]:
        """
        Get a comprehensive economic dashboard with key indicators
        
        Returns:
            Dictionary with economic dashboard data
        """
        try:
            # Get key economic indicators
            dashboard_data = {}
            
            # GDP
            gdp_data = await self.get_gdp_data()
            if not gdp_data.empty:
                latest_gdp = gdp_data.iloc[-1]['value']
                gdp_growth = gdp_data.pct_change(periods=4).iloc[-1] * 100  # Year-over-year
                dashboard_data['gdp'] = {
                    'latest_value': latest_gdp,
                    'yoy_growth': gdp_growth,
                    'last_updated': gdp_data.index[-1].strftime('%Y-%m-%d'),
                }
            
            # Inflation
            inflation_data = await self.get_inflation_data()
            if not inflation_data.empty:
                latest_cpi = inflation_data.iloc[-1]['value']
                inflation_rate = inflation_data.pct_change(periods=12).iloc[-1] * 100  # Year-over-year
                dashboard_data['inflation'] = {
                    'latest_value': latest_cpi,
                    'yoy_change': inflation_rate,
                    'last_updated': inflation_data.index[-1].strftime('%Y-%m-%d'),
                }
            
            # Employment
            employment_data = await self.get_employment_data()
            if 'UNRATE' in employment_data and not employment_data['UNRATE'].empty:
                unemployment_rate = employment_data['UNRATE'].iloc[-1]['value']
                dashboard_data['unemployment'] = {
                    'rate': unemployment_rate,
                    'last_updated': employment_data['UNRATE'].index[-1].strftime('%Y-%m-%d'),
                }
            
            # Interest Rates
            rate_data = await self.get_interest_rates()
            if 'FEDFUNDS' in rate_data and not rate_data['FEDFUNDS'].empty:
                fed_funds = rate_data['FEDFUNDS'].iloc[-1]['value']
                dashboard_data['fed_funds_rate'] = {
                    'rate': fed_funds,
                    'last_updated': rate_data['FEDFUNDS'].index[-1].strftime('%Y-%m-%d'),
                }
            
            if 'DGS10' in rate_data and not rate_data['DGS10'].empty:
                treasury_10y = rate_data['DGS10'].iloc[-1]['value']
                dashboard_data['10y_treasury'] = {
                    'yield': treasury_10y,
                    'last_updated': rate_data['DGS10'].index[-1].strftime('%Y-%m-%d'),
                }
            
            return dashboard_data
            
        except Exception as e:
            raise ValueError(f"Failed to get economic dashboard: {str(e)}")
    
    async def calculate_yoy_change(self, series_id: str) -> pd.DataFrame:
        """
        Calculate year-over-year change for a series
        
        Args:
            series_id: FRED series ID
            
        Returns:
            DataFrame with YoY changes
        """
        data = await self.get_data(series_id)
        
        # Calculate year-over-year change
        yoy_change = data.pct_change(periods=12) * 100
        yoy_change.columns = ['yoy_change']
        
        return yoy_change
    
    async def calculate_moving_average(self, series_id: str, window: int = 12) -> pd.DataFrame:
        """
        Calculate moving average for a series
        
        Args:
            series_id: FRED series ID
            window: Moving average window in months
            
        Returns:
            DataFrame with moving average
        """
        data = await self.get_data(series_id)
        
        # Calculate moving average
        ma = data.rolling(window=window).mean()
        ma.columns = ['moving_average']
        
        return ma
