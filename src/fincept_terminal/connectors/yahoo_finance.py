"""
Yahoo Finance Data Connector
Provides comprehensive market data, financial statements, and real-time quotes
"""

import asyncio
import aiohttp
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class YahooData:
    """Data structure for Yahoo Finance data"""
    symbol: str
    price_data: pd.DataFrame
    financials: Dict[str, pd.DataFrame]
    info: Dict[str, Any]
    dividends: pd.DataFrame
    splits: pd.DataFrame
    actions: pd.DataFrame


class YahooFinanceConnector:
    """
    Yahoo Finance data connector for comprehensive financial data.
    
    Features:
    - Real-time and historical price data
    - Financial statements (income statement, balance sheet, cash flow)
    - Company information and key metrics
    - Dividends and stock splits
    - Options data
    - Analyst recommendations
    - News and earnings calendar
    """
    
    def __init__(self):
        self.base_url = "https://query1.finance.yahoo.com/v8/finance/chart"
        self.session = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def get_data(self, symbol: str, period: str = "1y", 
                     interval: str = "1d") -> pd.DataFrame:
        """
        Get historical price data for a symbol
        
        Args:
            symbol: Stock ticker symbol
            period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)
            
        Returns:
            DataFrame with OHLCV data
        """
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period, interval=interval)
            
            if data.empty:
                raise ValueError(f"No data found for symbol {symbol}")
            
            # Add technical indicators
            data = self._add_technical_indicators(data)
            
            return data
            
        except Exception as e:
            raise ValueError(f"Failed to get Yahoo Finance data for {symbol}: {str(e)}")
    
    async def get_financial_data(self, symbol: str) -> YahooData:
        """
        Get comprehensive financial data for a symbol
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            YahooData object with all available information
        """
        try:
            ticker = yf.Ticker(symbol)
            
            # Get price data
            price_data = ticker.history(period="2y")
            
            # Get financial statements
            financials = {
                'income_statement': ticker.financials,
                'quarterly_income': ticker.quarterly_financials,
                'balance_sheet': ticker.balance_sheet,
                'quarterly_balance': ticker.quarterly_balance_sheet,
                'cash_flow': ticker.cashflow,
                'quarterly_cash_flow': ticker.quarterly_cashflow,
            }
            
            # Get company info
            info = ticker.info
            
            # Get dividends and splits
            dividends = ticker.dividends
            splits = ticker.splits
            actions = ticker.actions
            
            return YahooData(
                symbol=symbol.upper(),
                price_data=price_data,
                financials=financials,
                info=info,
                dividends=dividends,
                splits=splits,
                actions=actions
            )
            
        except Exception as e:
            raise ValueError(f"Failed to get financial data for {symbol}: {str(e)}")
    
    async def get_real_time_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Get real-time quote data
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Dictionary with real-time quote information
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            quote = {
                'symbol': symbol.upper(),
                'price': info.get('currentPrice', 0),
                'change': info.get('regularMarketChange', 0),
                'change_percent': info.get('regularMarketChangePercent', 0),
                'volume': info.get('volume', 0),
                'avg_volume': info.get('averageVolume', 0),
                'market_cap': info.get('marketCap', 0),
                'pe_ratio': info.get('trailingPE', 0),
                'bid': info.get('bid', 0),
                'ask': info.get('ask', 0),
                'bid_size': info.get('bidSize', 0),
                'ask_size': info.get('askSize', 0),
                'day_high': info.get('dayHigh', 0),
                'day_low': info.get('dayLow', 0),
                '52_week_high': info.get('fiftyTwoWeekHigh', 0),
                '52_week_low': info.get('fiftyTwoWeekLow', 0),
                'timestamp': datetime.now().isoformat(),
            }
            
            return quote
            
        except Exception as e:
            raise ValueError(f"Failed to get real-time quote for {symbol}: {str(e)}")
    
    async def get_multiple_quotes(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Get real-time quotes for multiple symbols
        
        Args:
            symbols: List of stock ticker symbols
            
        Returns:
            Dictionary with quotes for each symbol
        """
        quotes = {}
        
        # Process in batches to avoid rate limiting
        batch_size = 10
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i + batch_size]
            
            for symbol in batch:
                try:
                    quote = await self.get_real_time_quote(symbol)
                    quotes[symbol.upper()] = quote
                except Exception as e:
                    quotes[symbol.upper()] = {'error': str(e)}
            
            # Small delay between batches
            if i + batch_size < len(symbols):
                await asyncio.sleep(0.1)
        
        return quotes
    
    async def get_options_chain(self, symbol: str, expiration: Optional[str] = None) -> Dict[str, pd.DataFrame]:
        """
        Get options chain for a symbol
        
        Args:
            symbol: Stock ticker symbol
            expiration: Options expiration date (YYYY-MM-DD format)
            
        Returns:
            Dictionary with calls and puts DataFrames
        """
        try:
            ticker = yf.Ticker(symbol)
            options = ticker.option_chain(date=expiration)
            
            return {
                'calls': options.calls,
                'puts': options.puts,
                'expirations': ticker.options
            }
            
        except Exception as e:
            raise ValueError(f"Failed to get options chain for {symbol}: {str(e)}")
    
    async def get_analyst_recommendations(self, symbol: str) -> pd.DataFrame:
        """
        Get analyst recommendations for a symbol
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            DataFrame with analyst recommendations
        """
        try:
            ticker = yf.Ticker(symbol)
            recommendations = ticker.recommendations
            
            if recommendations is None or recommendations.empty:
                # Return empty DataFrame with expected columns
                return pd.DataFrame(columns=[
                    'Firm', 'To Grade', 'From Grade', 'Action', 'Date'
                ])
            
            return recommendations
            
        except Exception as e:
            raise ValueError(f"Failed to get analyst recommendations for {symbol}: {str(e)}")
    
    async def get_earnings_calendar(self, symbol: str) -> pd.DataFrame:
        """
        Get earnings calendar for a symbol
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            DataFrame with earnings dates and estimates
        """
        try:
            ticker = yf.Ticker(symbol)
            calendar = ticker.calendar
            
            if calendar is None:
                # Return empty DataFrame with expected columns
                return pd.DataFrame(columns=[
                    'Earnings Date', 'Earnings Average', 'Earnings Low', 'Earnings High',
                    'Revenue Average', 'Revenue Low', 'Revenue High'
                ])
            
            return calendar
            
        except Exception as e:
            raise ValueError(f"Failed to get earnings calendar for {symbol}: {str(e)}")
    
    async def get_news(self, symbol: str, count: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent news for a symbol
        
        Args:
            symbol: Stock ticker symbol
            count: Number of news items to retrieve
            
        Returns:
            List of news items
        """
        try:
            ticker = yf.Ticker(symbol)
            news = ticker.news
            
            if not news:
                return []
            
            formatted_news = []
            for item in news[:count]:
                content = item.get('content') or item
                provider = content.get('provider') or {}
                link = item.get('link', '')
                for key in ('clickThroughUrl', 'canonicalUrl'):
                    url_obj = content.get(key) or item.get(key)
                    if isinstance(url_obj, dict) and url_obj.get('url'):
                        link = url_obj['url']
                        break
                formatted_news.append({
                    'title': content.get('title') or item.get('title', ''),
                    'publisher': provider.get('displayName') or item.get('publisher', ''),
                    'link': link,
                    'published': (
                        content.get('displayTime')
                        or content.get('pubDate')
                        or item.get('providerPublishTime', '')
                    ),
                    'summary': content.get('summary') or item.get('summary', ''),
                })

            return formatted_news
            
        except Exception as e:
            raise ValueError(f"Failed to get news for {symbol}: {str(e)}")
    
    async def search_symbols(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for symbols based on query
        
        Args:
            query: Search query (company name or symbol)
            
        Returns:
            List of matching symbols
        """
        try:
            # Yahoo Finance doesn't have a direct search API in yfinance
            # This is a simplified implementation
            import requests
            
            search_url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}"
            response = requests.get(search_url, headers={'User-Agent': 'Mozilla/5.0'})
            
            if response.status_code == 200:
                data = response.json()
                results = []
                
                for item in data.get('quotes', [])[:10]:  # Limit to 10 results
                    results.append({
                        'symbol': item.get('symbol', ''),
                        'name': item.get('longname', item.get('shortname', '')),
                        'type': item.get('quoteType', ''),
                        'exchange': item.get('exchange', ''),
                    })
                
                return results
            
            return []
            
        except Exception as e:
            raise ValueError(f"Failed to search symbols: {str(e)}")
    
    async def get_sector_data(self, sector: str) -> Dict[str, pd.DataFrame]:
        """
        Get data for all stocks in a sector
        
        Args:
            sector: Sector name (e.g., 'Technology', 'Healthcare')
            
        Returns:
            Dictionary with sector data
        """
        try:
            # This is a simplified implementation
            # In practice, you'd use a sector ETF or maintain a sector mapping
            
            sector_etfs = {
                'Technology': 'XLK',
                'Healthcare': 'XLV',
                'Financial': 'XLF',
                'Energy': 'XLE',
                'Consumer Discretionary': 'XLY',
                'Consumer Staples': 'XLP',
                'Industrial': 'XLI',
                'Materials': 'XLB',
                'Real Estate': 'XLRE',
                'Utilities': 'XLU',
                'Communication': 'XLC',
            }
            
            etf_symbol = sector_etfs.get(sector, 'SPY')
            
            ticker = yf.Ticker(etf_symbol)
            price_data = ticker.history(period="1y")
            info = ticker.info
            
            # Get top holdings (simplified)
            holdings = info.get('holdings', [])
            
            return {
                'etf_data': price_data,
                'etf_info': info,
                'holdings': holdings,
                'sector': sector,
            }
            
        except Exception as e:
            raise ValueError(f"Failed to get sector data for {sector}: {str(e)}")
    
    def _add_technical_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Add common technical indicators to price data"""
        try:
            # Moving averages
            data['MA20'] = data['Close'].rolling(window=20).mean()
            data['MA50'] = data['Close'].rolling(window=50).mean()
            data['MA200'] = data['Close'].rolling(window=200).mean()
            
            # RSI
            delta = data['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            data['RSI'] = 100 - (100 / (1 + rs))
            
            # MACD
            exp1 = data['Close'].ewm(span=12).mean()
            exp2 = data['Close'].ewm(span=26).mean()
            data['MACD'] = exp1 - exp2
            data['MACD_Signal'] = data['MACD'].ewm(span=9).mean()
            data['MACD_Histogram'] = data['MACD'] - data['MACD_Signal']
            
            # Bollinger Bands
            data['BB_Middle'] = data['Close'].rolling(window=20).mean()
            bb_std = data['Close'].rolling(window=20).std()
            data['BB_Upper'] = data['BB_Middle'] + (bb_std * 2)
            data['BB_Lower'] = data['BB_Middle'] - (bb_std * 2)
            
            # Volume indicators
            data['Volume_MA20'] = data['Volume'].rolling(window=20).mean()
            data['Volume_Ratio'] = data['Volume'] / data['Volume_MA20']
            
            return data
            
        except Exception:
            # Return original data if indicators fail
            return data
    
    async def validate_symbol(self, symbol: str) -> bool:
        """
        Validate if a symbol exists and is tradeable
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            True if symbol is valid, False otherwise
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # Check if we got valid data
            return (info.get('symbol') is not None and 
                   info.get('regularMarketPrice') is not None)
                   
        except Exception:
            return False
    
    async def get_market_status(self) -> Dict[str, Any]:
        """
        Get current market status and trading hours
        
        Returns:
            Dictionary with market status information
        """
        try:
            # Get major indices
            indices = ['^GSPC', '^DJI', '^IXIC', '^VIX']
            quotes = await self.get_multiple_quotes(indices)
            
            # Determine market status (simplified)
            current_time = datetime.now().time()
            market_open = current_time >= datetime.strptime('09:30', '%H:%M').time() and \
                          current_time <= datetime.strptime('16:00', '%H:%M').time()
            
            return {
                'market_open': market_open,
                'current_time': datetime.now().isoformat(),
                'indices': quotes,
                'next_open': datetime.now().replace(hour=9, minute=30, second=0).isoformat() if not market_open else None,
                'next_close': datetime.now().replace(hour=16, minute=0, second=0).isoformat() if market_open else None,
            }
            
        except Exception as e:
            raise ValueError(f"Failed to get market status: {str(e)}")
