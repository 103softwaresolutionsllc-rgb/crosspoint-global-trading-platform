"""
Kraken Cryptocurrency Exchange Connector
Provides real-time and historical cryptocurrency data from Kraken exchange
"""

import asyncio
import aiohttp
import pandas as pd
import websockets
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class KrakenTicker:
    """Data structure for Kraken ticker data"""
    pair: str
    last: float
    bid: float
    ask: float
    volume: float
    vwap: float
    low: float
    high: float
    open: float
    timestamp: datetime


class KrakenConnector:
    """
    Kraken exchange connector for cryptocurrency data and trading.
    
    Features:
    - Real-time ticker data via WebSocket
    - Historical OHLCV data
    - Order book data
    - Recent trades
    - Account information
    - Trading operations
    - Market depth
    - Multiple trading pairs
    """
    
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = "https://api.kraken.com"
        self.ws_url = "wss://ws.kraken.com"
        self.session = None
        self.ws_connection = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
        if self.ws_connection:
            await self.ws_connection.close()
    
    async def get_data(self, pair: str, timeframe: str = "1D", 
                      since: Optional[int] = None) -> pd.DataFrame:
        """
        Get historical OHLCV data for a trading pair
        
        Args:
            pair: Trading pair (e.g., 'XBTUSD', 'ETHUSD')
            timeframe: Timeframe (1m, 5m, 15m, 30m, 1h, 4h, 1D, 1W)
            since: Unix timestamp for start time
            
        Returns:
            DataFrame with OHLCV data
        """
        try:
            # Map timeframe to Kraken interval
            interval_map = {
                '1m': 1, '5m': 5, '15m': 15, '30m': 30,
                '1h': 60, '4h': 240, '1D': 1440, '1W': 10080
            }
            
            if timeframe not in interval_map:
                raise ValueError(f"Invalid timeframe: {timeframe}")
            
            interval = interval_map[timeframe]
            
            # Build URL
            params = {
                'pair': pair,
                'interval': interval,
            }
            
            if since:
                params['since'] = since
            
            url = f"{self.base_url}/0/public/OHLC"
            
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    raise ValueError(f"Kraken API error: {response.status}")
                
                data = await response.json()
            
            if data['error']:
                raise ValueError(f"Kraken API error: {data['error']}")
            
            # Extract data
            result = data['result']
            if pair not in result:
                raise ValueError(f"No data found for pair {pair}")
            
            ohlc_data = result[pair]
            
            # Convert to DataFrame
            columns = ['timestamp', 'open', 'high', 'low', 'close', 'vwap', 'volume', 'count']
            df = pd.DataFrame(ohlc_data, columns=columns)
            
            # Convert data types
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
            for col in ['open', 'high', 'low', 'close', 'vwap', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            df.set_index('timestamp', inplace=True)
            
            # Add technical indicators
            df = self._add_crypto_indicators(df)
            
            return df
            
        except Exception as e:
            raise ValueError(f"Failed to get Kraken data for {pair}: {str(e)}")
    
    async def get_ticker(self, pair: str) -> KrakenTicker:
        """
        Get current ticker information for a pair
        
        Args:
            pair: Trading pair
            
        Returns:
            KrakenTicker object with current data
        """
        try:
            params = {'pair': pair}
            url = f"{self.base_url}/0/public/Ticker"
            
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    raise ValueError(f"Kraken API error: {response.status}")
                
                data = await response.json()
            
            if data['error']:
                raise ValueError(f"Kraken API error: {data['error']}")
            
            result = data['result']
            if pair not in result:
                raise ValueError(f"No ticker data found for {pair}")
            
            ticker_data = result[pair]
            
            return KrakenTicker(
                pair=pair,
                last=float(ticker_data['c'][0]),
                bid=float(ticker_data['b'][0]),
                ask=float(ticker_data['a'][0]),
                volume=float(ticker_data['v'][1]),  # 24h volume
                vwap=float(ticker_data['p'][1]),    # 24h vwap
                low=float(ticker_data['l'][1]),      # 24h low
                high=float(ticker_data['h'][1]),     # 24h high
                open=float(ticker_data['o']),         # 24h open
                timestamp=datetime.now()
            )
            
        except Exception as e:
            raise ValueError(f"Failed to get ticker for {pair}: {str(e)}")
    
    async def get_order_book(self, pair: str, count: int = 100) -> Dict[str, pd.DataFrame]:
        """
        Get order book for a pair
        
        Args:
            pair: Trading pair
            count: Number of price levels
            
        Returns:
            Dictionary with bids and asks DataFrames
        """
        try:
            params = {'pair': pair, 'count': count}
            url = f"{self.base_url}/0/public/Depth"
            
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    raise ValueError(f"Kraken API error: {response.status}")
                
                data = await response.json()
            
            if data['error']:
                raise ValueError(f"Kraken API error: {data['error']}")
            
            result = data['result']
            if pair not in result:
                raise ValueError(f"No order book data found for {pair}")
            
            book_data = result[pair]
            
            # Convert to DataFrames
            bids_df = pd.DataFrame(book_data['bids'], columns=['price', 'volume', 'timestamp'])
            asks_df = pd.DataFrame(book_data['asks'], columns=['price', 'volume', 'timestamp'])
            
            # Convert data types
            for df in [bids_df, asks_df]:
                df['price'] = pd.to_numeric(df['price'])
                df['volume'] = pd.to_numeric(df['volume'])
                df['timestamp'] = pd.to_numeric(df['timestamp'])
            
            return {
                'bids': bids_df,
                'asks': asks_df,
            }
            
        except Exception as e:
            raise ValueError(f"Failed to get order book for {pair}: {str(e)}")
    
    async def get_recent_trades(self, pair: str, since: Optional[int] = None) -> pd.DataFrame:
        """
        Get recent trades for a pair
        
        Args:
            pair: Trading pair
            since: Unix timestamp for start time
            
        Returns:
            DataFrame with recent trades
        """
        try:
            params = {'pair': pair}
            if since:
                params['since'] = since
            
            url = f"{self.base_url}/0/public/Trades"
            
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    raise ValueError(f"Kraken API error: {response.status}")
                
                data = await response.json()
            
            if data['error']:
                raise ValueError(f"Kraken API error: {data['error']}")
            
            result = data['result']
            if pair not in result:
                raise ValueError(f"No trades data found for {pair}")
            
            trades_data = result[pair]
            
            # Convert to DataFrame
            df = pd.DataFrame(trades_data, columns=['price', 'volume', 'time', 'buy_sell', 'market_limit', 'misc'])
            
            # Convert data types
            df['price'] = pd.to_numeric(df['price'])
            df['volume'] = pd.to_numeric(df['volume'])
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df['buy_sell'] = df['buy_sell'].map({'b': 'buy', 's': 'sell'})
            
            df.set_index('time', inplace=True)
            
            return df[['price', 'volume', 'buy_sell']]
            
        except Exception as e:
            raise ValueError(f"Failed to get recent trades for {pair}: {str(e)}")
    
    async def get_asset_pairs(self) -> List[Dict[str, Any]]:
        """
        Get information about all tradable asset pairs
        
        Returns:
            List of asset pair information
        """
        try:
            url = f"{self.base_url}/0/public/AssetPairs"
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    raise ValueError(f"Kraken API error: {response.status}")
                
                data = await response.json()
            
            if data['error']:
                raise ValueError(f"Kraken API error: {data['error']}")
            
            pairs = []
            for pair_name, pair_info in data['result'].items():
                # Skip dark pool pairs (ending with .d)
                if pair_name.endswith('.d'):
                    continue
                
                pairs.append({
                    'name': pair_name,
                    'altname': pair_info['altname'],
                    'base': pair_info['base'],
                    'quote': pair_info['quote'],
                    'class': pair_info['aclass_base'],
                    'fee_volume_currency': pair_info['fee_volume_currency'],
                })
            
            return pairs
            
        except Exception as e:
            raise ValueError(f"Failed to get asset pairs: {str(e)}")
    
    async def subscribe_websocket(self, pairs: List[str], 
                               callback=None) -> None:
        """
        Subscribe to real-time data via WebSocket
        
        Args:
            pairs: List of trading pairs to subscribe to
            callback: Callback function for incoming data
        """
        try:
            self.ws_connection = await websockets.connect(self.ws_url)
            
            # Subscribe to ticker data
            subscribe_msg = {
                "event": "subscribe",
                "pair": pairs,
                "subscription": {"name": "ticker"}
            }
            
            await self.ws_connection.send(json.dumps(subscribe_msg))
            
            # Listen for messages
            async for message in self.ws_connection:
                data = json.loads(message)
                
                if callback:
                    await callback(data)
                else:
                    # Default handling
                    if data.get('event') == 'ticker':
                        await self._handle_ticker_message(data)
            
        except Exception as e:
            raise ValueError(f"WebSocket subscription failed: {str(e)}")
    
    async def _handle_ticker_message(self, data: Dict[str, Any]) -> None:
        """Handle incoming ticker WebSocket message"""
        try:
            if isinstance(data, dict) and 'data' in data:
                ticker_data = data['data']
                # Process ticker data
                print(f"Ticker update: {ticker_data}")
        except Exception as e:
            print(f"Error handling ticker message: {e}")
    
    async def get_account_balance(self) -> Dict[str, float]:
        """
        Get account balance (requires API credentials)
        
        Returns:
            Dictionary with asset balances
        """
        if not self.api_key or not self.api_secret:
            raise ValueError("API credentials required for account data")
        
        try:
            # This is a simplified implementation
            # In practice, you'd need to implement Kraken's authentication
            url = f"{self.base_url}/0/private/Balance"
            
            # Add authentication headers
            headers = self._get_auth_headers('/0/private/Balance', {})
            
            async with self.session.post(url, headers=headers) as response:
                if response.status != 200:
                    raise ValueError(f"Kraken API error: {response.status}")
                
                data = await response.json()
            
            if data['error']:
                raise ValueError(f"Kraken API error: {data['error']}")
            
            return data['result']
            
        except Exception as e:
            raise ValueError(f"Failed to get account balance: {str(e)}")
    
    async def place_order(self, pair: str, side: str, order_type: str,
                        volume: float, price: Optional[float] = None) -> Dict[str, Any]:
        """
        Place a trading order (requires API credentials)
        
        Args:
            pair: Trading pair
            side: 'buy' or 'sell'
            order_type: 'market', 'limit', 'stop-loss', etc.
            volume: Order volume
            price: Order price (required for limit orders)
            
        Returns:
            Dictionary with order information
        """
        if not self.api_key or not self.api_secret:
            raise ValueError("API credentials required for trading")
        
        try:
            params = {
                'pair': pair,
                'type': side,
                'ordertype': order_type,
                'volume': str(volume),
            }
            
            if price:
                params['price'] = str(price)
            
            url = f"{self.base_url}/0/private/AddOrder"
            headers = self._get_auth_headers('/0/private/AddOrder', params)
            
            async with self.session.post(url, data=params, headers=headers) as response:
                if response.status != 200:
                    raise ValueError(f"Kraken API error: {response.status}")
                
                data = await response.json()
            
            if data['error']:
                raise ValueError(f"Kraken API error: {data['error']}")
            
            return data['result']
            
        except Exception as e:
            raise ValueError(f"Failed to place order: {str(e)}")
    
    def _get_auth_headers(self, endpoint: str, params: Dict[str, str]) -> Dict[str, str]:
        """
        Generate authentication headers for private API calls
        
        Args:
            endpoint: API endpoint
            params: Request parameters
            
        Returns:
            Dictionary with authentication headers
        """
        # This is a simplified implementation
        # In practice, you'd implement Kraken's specific authentication method
        import hashlib
        import hmac
        import base64
        import urllib.parse
        
        # Create nonce
        nonce = str(int(datetime.now().timestamp() * 1000))
        
        # Create signature
        post_data = urllib.parse.urlencode(params)
        message = nonce + post_data
        signature = hmac.new(
            self.api_secret.encode(),
            message.encode(),
            hashlib.sha256
        ).digest()
        
        signature_b64 = base64.b64encode(signature).decode()
        
        return {
            'API-Key': self.api_key,
            'API-Sign': signature_b64,
        }
    
    def _add_crypto_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add cryptocurrency-specific technical indicators"""
        try:
            # Moving averages
            df['MA20'] = df['close'].rolling(window=20).mean()
            df['MA50'] = df['close'].rolling(window=50).mean()
            df['MA200'] = df['close'].rolling(window=200).mean()
            
            # RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))
            
            # MACD
            exp1 = df['close'].ewm(span=12).mean()
            exp2 = df['close'].ewm(span=26).mean()
            df['MACD'] = exp1 - exp2
            df['MACD_Signal'] = df['MACD'].ewm(span=9).mean()
            df['MACD_Histogram'] = df['MACD'] - df['MACD_Signal']
            
            # Bollinger Bands
            df['BB_Middle'] = df['close'].rolling(window=20).mean()
            bb_std = df['close'].rolling(window=20).std()
            df['BB_Upper'] = df['BB_Middle'] + (bb_std * 2)
            df['BB_Lower'] = df['BB_Middle'] - (bb_std * 2)
            
            # Volume indicators
            df['Volume_MA20'] = df['volume'].rolling(window=20).mean()
            df['Volume_Ratio'] = df['volume'] / df['Volume_MA20']
            
            # Price change
            df['Price_Change'] = df['close'].pct_change()
            df['Price_Change_Std'] = df['Price_Change'].rolling(window=20).std()
            
            # Volatility
            df['Volatility'] = df['Price_Change'].rolling(window=20).std() * np.sqrt(252)
            
            return df
            
        except Exception:
            # Return original data if indicators fail
            return df
    
    async def get_market_summary(self) -> Dict[str, Any]:
        """
        Get market summary for major cryptocurrencies
        
        Returns:
            Dictionary with market summary data
        """
        try:
            # Major crypto pairs
            major_pairs = ['XBTUSD', 'ETHUSD', 'LTCUSD', 'XRPUSD', 'ADAUSD']
            
            summary = {}
            
            for pair in major_pairs:
                try:
                    ticker = await self.get_ticker(pair)
                    summary[pair] = {
                        'price': ticker.last,
                        'change': ticker.last - ticker.open,
                        'change_percent': ((ticker.last - ticker.open) / ticker.open) * 100,
                        'volume': ticker.volume,
                        'high': ticker.high,
                        'low': ticker.low,
                    }
                except Exception as e:
                    summary[pair] = {'error': str(e)}
            
            return summary
            
        except Exception as e:
            raise ValueError(f"Failed to get market summary: {str(e)}")
    
    async def calculate_spread(self, pair: str) -> Dict[str, float]:
        """
        Calculate bid-ask spread for a pair
        
        Args:
            pair: Trading pair
            
        Returns:
            Dictionary with spread information
        """
        try:
            ticker = await self.get_ticker(pair)
            
            spread = ticker.ask - ticker.bid
            spread_percent = (spread / ticker.bid) * 100
            
            return {
                'bid': ticker.bid,
                'ask': ticker.ask,
                'spread': spread,
                'spread_percent': spread_percent,
                'mid_price': (ticker.bid + ticker.ask) / 2,
            }
            
        except Exception as e:
            raise ValueError(f"Failed to calculate spread for {pair}: {str(e)}")
