"""
WebSocket Manager for Real-Time Trading
Real-time data feeds and WebSocket connections for multiple exchanges
"""

import asyncio
import websockets
import json
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from datetime import datetime
import pandas as pd
from collections import defaultdict
import aiohttp


@dataclass
class MarketData:
    """Real-time market data structure"""
    symbol: str
    timestamp: datetime
    price: float
    volume: float
    bid: Optional[float] = None
    ask: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    open: Optional[float] = None
    close: Optional[float] = None
    exchange: Optional[str] = None


@dataclass
class TradeData:
    """Real-time trade data structure"""
    symbol: str
    timestamp: datetime
    price: float
    size: float
    side: str  # 'buy' or 'sell'
    trade_id: Optional[str] = None
    exchange: Optional[str] = None


@dataclass
class OrderBookData:
    """Real-time order book data structure"""
    symbol: str
    timestamp: datetime
    bids: List[List[float]]  # [price, size]
    asks: List[List[float]]  # [price, size]
    exchange: Optional[str] = None


class WebSocketManager:
    """
    WebSocket manager for real-time market data from multiple exchanges.
    
    Features:
    - Multi-exchange WebSocket connections
    - Real-time price feeds
    - Trade data streams
    - Order book updates
    - Automatic reconnection
    - Data normalization
    - Subscription management
    """
    
    def __init__(self):
        self.connections: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.subscriptions: Dict[str, set] = defaultdict(set)
        self.data_handlers: Dict[str, List[Callable]] = defaultdict(list)
        self.reconnect_attempts: Dict[str, int] = defaultdict(int)
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 5  # seconds
        self.logger = logging.getLogger(__name__)
        
    async def connect_to_exchange(self, exchange: str, symbols: List[str]) -> bool:
        """
        Connect to exchange WebSocket
        
        Args:
            exchange: Exchange name ('binance', 'kraken', 'polygon', etc.)
            symbols: List of symbols to subscribe to
            
        Returns:
            True if connection successful
        """
        try:
            if exchange.lower() == 'binance':
                return await self._connect_binance(symbols)
            elif exchange.lower() == 'kraken':
                return await self._connect_kraken(symbols)
            elif exchange.lower() == 'polygon':
                return await self._connect_polygon(symbols)
            elif exchange.lower() == 'alpaca':
                return await self._connect_alpaca(symbols)
            else:
                self.logger.error(f"Unsupported exchange: {exchange}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to connect to {exchange}: {e}")
            return False
    
    async def _connect_binance(self, symbols: List[str]) -> bool:
        """Connect to Binance WebSocket"""
        try:
            # Format symbols for Binance
            formatted_symbols = [symbol.lower() + '@trade' for symbol in symbols]
            stream = '/'.join(formatted_symbols)
            url = f"wss://stream.binance.com:9443/ws/{stream}"
            
            ws = await websockets.connect(url)
            self.connections['binance'] = ws
            
            # Start message handler
            asyncio.create_task(self._handle_binance_messages(ws))
            
            self.logger.info(f"Connected to Binance with symbols: {symbols}")
            return True
            
        except Exception as e:
            self.logger.error(f"Binance connection failed: {e}")
            return False
    
    async def _connect_kraken(self, symbols: List[str]) -> bool:
        """Connect to Kraken WebSocket"""
        try:
            url = "wss://ws.kraken.com/"
            ws = await websockets.connect(url)
            self.connections['kraken'] = ws
            
            # Subscribe to symbols
            subscribe_msg = {
                "event": "subscribe",
                "pair": symbols,
                "subscription": {"name": "ticker"}
            }
            
            await ws.send(json.dumps(subscribe_msg))
            
            # Start message handler
            asyncio.create_task(self._handle_kraken_messages(ws))
            
            self.logger.info(f"Connected to Kraken with symbols: {symbols}")
            return True
            
        except Exception as e:
            self.logger.error(f"Kraken connection failed: {e}")
            return False
    
    async def _connect_polygon(self, symbols: List[str]) -> bool:
        """Connect to Polygon WebSocket"""
        try:
            # Polygon requires API key
            api_key = "YOUR_POLYGON_API_KEY"  # User should provide their own
            url = f"wss://socket.polygon.io/stocks"
            
            ws = await websockets.connect(url)
            self.connections['polygon'] = ws
            
            # Authenticate
            auth_msg = {"action": "auth", "params": api_key}
            await ws.send(json.dumps(auth_msg))
            
            # Subscribe to symbols
            for symbol in symbols:
                subscribe_msg = {
                    "action": "subscribe",
                    "params": f"T.{symbol}"
                }
                await ws.send(json.dumps(subscribe_msg))
            
            # Start message handler
            asyncio.create_task(self._handle_polygon_messages(ws))
            
            self.logger.info(f"Connected to Polygon with symbols: {symbols}")
            return True
            
        except Exception as e:
            self.logger.error(f"Polygon connection failed: {e}")
            return False
    
    async def _connect_alpaca(self, symbols: List[str]) -> bool:
        """Connect to Alpaca WebSocket"""
        try:
            # Alpaca requires API credentials
            api_key = "YOUR_ALPACA_API_KEY"
            secret_key = "YOUR_ALPACA_SECRET_KEY"
            
            url = "wss://stream.data.alpaca.markets/v2/iex"
            ws = await websockets.connect(url)
            self.connections['alpaca'] = ws
            
            # Authenticate
            auth_msg = {
                "action": "auth",
                "key": api_key,
                "secret": secret_key
            }
            await ws.send(json.dumps(auth_msg))
            
            # Subscribe to symbols
            subscribe_msg = {
                "action": "subscribe",
                "trades": symbols,
                "quotes": symbols,
                "bars": symbols
            }
            await ws.send(json.dumps(subscribe_msg))
            
            # Start message handler
            asyncio.create_task(self._handle_alpaca_messages(ws))
            
            self.logger.info(f"Connected to Alpaca with symbols: {symbols}")
            return True
            
        except Exception as e:
            self.logger.error(f"Alpaca connection failed: {e}")
            return False
    
    async def _handle_binance_messages(self, ws: websockets.WebSocketServerProtocol):
        """Handle Binance WebSocket messages"""
        try:
            async for message in ws:
                data = json.loads(message)
                
                if 'e' in data:  # Trade event
                    trade_data = TradeData(
                        symbol=data['s'],
                        timestamp=datetime.fromtimestamp(data['T'] / 1000),
                        price=float(data['p']),
                        size=float(data['q']),
                        side='buy' if data['m'] else 'sell',
                        trade_id=str(data['t']),
                        exchange='binance'
                    )
                    
                    await self._emit_data('trade', trade_data)
                    
        except websockets.exceptions.ConnectionClosed:
            await self._handle_reconnect('binance')
        except Exception as e:
            self.logger.error(f"Binance message handler error: {e}")
    
    async def _handle_kraken_messages(self, ws: websockets.WebSocketServerProtocol):
        """Handle Kraken WebSocket messages"""
        try:
            async for message in ws:
                data = json.loads(message)
                
                if data.get('event') == 'trade':
                    for trade in data.get('data', []):
                        market_data = MarketData(
                            symbol=trade[1],
                            timestamp=datetime.fromtimestamp(float(trade[2])),
                            price=float(trade[0]),
                            volume=float(trade[3]),
                            exchange='kraken'
                        )
                        
                        await self._emit_data('quote', market_data)
                        
        except websockets.exceptions.ConnectionClosed:
            await self._handle_reconnect('kraken')
        except Exception as e:
            self.logger.error(f"Kraken message handler error: {e}")
    
    async def _handle_polygon_messages(self, ws: websockets.WebSocketServerProtocol):
        """Handle Polygon WebSocket messages"""
        try:
            async for message in ws:
                data = json.loads(message)
                
                for msg in data:
                    if msg['ev'] == 'T':  # Trade event
                        trade_data = TradeData(
                            symbol=msg['sym'],
                            timestamp=datetime.fromtimestamp(msg['t'] / 1000),
                            price=float(msg['p']),
                            size=float(msg['s']),
                            side='buy' if msg['x'] == 1 else 'sell',
                            trade_id=str(msg['i']),
                            exchange='polygon'
                        )
                        
                        await self._emit_data('trade', trade_data)
                        
        except websockets.exceptions.ConnectionClosed:
            await self._handle_reconnect('polygon')
        except Exception as e:
            self.logger.error(f"Polygon message handler error: {e}")
    
    async def _handle_alpaca_messages(self, ws: websockets.WebSocketServerProtocol):
        """Handle Alpaca WebSocket messages"""
        try:
            async for message in ws:
                data = json.loads(message)
                
                for msg in data:
                    if msg['T'] == 't':  # Trade event
                        trade_data = TradeData(
                            symbol=msg['S'],
                            timestamp=datetime.fromtimestamp(msg['t'] / 1000000000),
                            price=float(msg['p']),
                            size=float(msg['s']),
                            side='buy' if msg['S'] == 1 else 'sell',
                            trade_id=str(msg['i']),
                            exchange='alpaca'
                        )
                        
                        await self._emit_data('trade', trade_data)
                        
                    elif msg['T'] == 'q':  # Quote event
                        market_data = MarketData(
                            symbol=msg['S'],
                            timestamp=datetime.fromtimestamp(msg['t'] / 1000000000),
                            price=(float(msg['bp']) + float(msg['ap'])) / 2,
                            volume=0,
                            bid=float(msg['bp']),
                            ask=float(msg['ap']),
                            exchange='alpaca'
                        )
                        
                        await self._emit_data('quote', market_data)
                        
        except websockets.exceptions.ConnectionClosed:
            await self._handle_reconnect('alpaca')
        except Exception as e:
            self.logger.error(f"Alpaca message handler error: {e}")
    
    async def _handle_reconnect(self, exchange: str):
        """Handle WebSocket reconnection"""
        self.reconnect_attempts[exchange] += 1
        
        if self.reconnect_attempts[exchange] <= self.max_reconnect_attempts:
            self.logger.info(f"Attempting to reconnect to {exchange} (attempt {self.reconnect_attempts[exchange]})")
            
            await asyncio.sleep(self.reconnect_delay)
            
            # Reconnect with previous subscriptions
            symbols = list(self.subscriptions.get(exchange, set()))
            if symbols:
                await self.connect_to_exchange(exchange, symbols)
        else:
            self.logger.error(f"Max reconnection attempts reached for {exchange}")
    
    async def _emit_data(self, data_type: str, data: Any):
        """Emit data to registered handlers"""
        for handler in self.data_handlers[data_type]:
            try:
                await handler(data)
            except Exception as e:
                self.logger.error(f"Data handler error: {e}")
    
    def add_data_handler(self, data_type: str, handler: Callable):
        """Add a data handler for specific data type"""
        self.data_handlers[data_type].append(handler)
    
    def remove_data_handler(self, data_type: str, handler: Callable):
        """Remove a data handler"""
        if handler in self.data_handlers[data_type]:
            self.data_handlers[data_type].remove(handler)
    
    async def subscribe_to_symbol(self, exchange: str, symbol: str):
        """Subscribe to a symbol on an exchange"""
        self.subscriptions[exchange].add(symbol)
        
        # If already connected, send subscription message
        if exchange in self.connections:
            await self._send_subscription(exchange, symbol)
    
    async def unsubscribe_from_symbol(self, exchange: str, symbol: str):
        """Unsubscribe from a symbol on an exchange"""
        self.subscriptions[exchange].discard(symbol)
        
        # If connected, send unsubscription message
        if exchange in self.connections:
            await self._send_unsubscription(exchange, symbol)
    
    async def _send_subscription(self, exchange: str, symbol: str):
        """Send subscription message to exchange"""
        try:
            ws = self.connections[exchange]
            
            if exchange == 'kraken':
                msg = {
                    "event": "subscribe",
                    "pair": [symbol],
                    "subscription": {"name": "ticker"}
                }
                await ws.send(json.dumps(msg))
                
        except Exception as e:
            self.logger.error(f"Failed to send subscription: {e}")
    
    async def _send_unsubscription(self, exchange: str, symbol: str):
        """Send unsubscription message to exchange"""
        try:
            ws = self.connections[exchange]
            
            if exchange == 'kraken':
                msg = {
                    "event": "unsubscribe",
                    "pair": [symbol],
                    "subscription": {"name": "ticker"}
                }
                await ws.send(json.dumps(msg))
                
        except Exception as e:
            self.logger.error(f"Failed to send unsubscription: {e}")
    
    async def disconnect_all(self):
        """Disconnect from all exchanges"""
        for exchange, ws in self.connections.items():
            try:
                await ws.close()
                self.logger.info(f"Disconnected from {exchange}")
            except Exception as e:
                self.logger.error(f"Error disconnecting from {exchange}: {e}")
        
        self.connections.clear()
        self.subscriptions.clear()
    
    def get_connection_status(self) -> Dict[str, bool]:
        """Get connection status for all exchanges"""
        return {
            exchange: ws.open if ws else False
            for exchange, ws in self.connections.items()
        }


class RealTimeDataFeed:
    """
    Real-time data feed manager for trading applications.
    
    Features:
    - Unified data interface
    - Data caching and buffering
    - Technical indicator calculation
    - Alert system
    - Historical data integration
    - Liquidity gate hooks (OBI / spread toxicity)
    """
    
    def __init__(self, websocket_manager: WebSocketManager, liquidity_gate=None):
        self.ws_manager = websocket_manager
        self.data_cache: Dict[str, List[MarketData]] = defaultdict(list)
        self.trade_cache: Dict[str, List[TradeData]] = defaultdict(list)
        self.orderbook_cache: Dict[str, OrderBookData] = {}
        self.alerts: List[Dict[str, Any]] = []
        self.indicators: Dict[str, Dict[str, float]] = defaultdict(dict)
        self.max_cache_size = 1000
        self.liquidity_gate = liquidity_gate
        self._banner_callbacks: List[Callable] = []
        
        # Register data handlers
        self.ws_manager.add_data_handler('quote', self._handle_market_data)
        self.ws_manager.add_data_handler('trade', self._handle_trade_data)
        self.ws_manager.add_data_handler('orderbook', self._handle_order_book)
    
    async def _handle_market_data(self, data: MarketData):
        """Handle incoming market data"""
        symbol = data.symbol
        
        # Add to cache
        self.data_cache[symbol].append(data)
        
        # Limit cache size
        if len(self.data_cache[symbol]) > self.max_cache_size:
            self.data_cache[symbol].pop(0)
        
        # Calculate indicators
        await self._update_indicators(symbol)
        
        # Check alerts
        await self._check_alerts(symbol, data)

        if data.bid and data.ask and self.liquidity_gate is not None:
            self.liquidity_gate.on_quote_spread(symbol, data.bid, data.ask)

        if self._banner_callbacks and len(self.data_cache[symbol]) >= 2:
            prev = self.data_cache[symbol][-2].price
            chg = ((data.price / prev) - 1) * 100 if prev else 0.0
            self.emit_quote_to_banner(symbol, data.price, chg)
    
    async def _handle_trade_data(self, data: TradeData):
        """Handle incoming trade data"""
        symbol = data.symbol
        
        # Add to cache
        self.trade_cache[symbol].append(data)
        
        # Limit cache size
        if len(self.trade_cache[symbol]) > self.max_cache_size:
            self.trade_cache[symbol].pop(0)

        # Keep quote cache warm from trades for get_latest_price
        quote = MarketData(
            symbol=symbol,
            timestamp=data.timestamp,
            price=data.price,
            volume=data.size,
            exchange=data.exchange,
        )
        self.data_cache[symbol].append(quote)
        if len(self.data_cache[symbol]) > self.max_cache_size:
            self.data_cache[symbol].pop(0)

    async def _handle_order_book(self, data: OrderBookData):
        """Handle order book updates and feed liquidity gate."""
        self.orderbook_cache[data.symbol] = data
        if self.liquidity_gate is not None:
            self.liquidity_gate.on_order_book(data)

    def add_banner_callback(self, callback: Callable) -> None:
        """Register UI callback: fn(symbol, price, change_pct)."""
        self._banner_callbacks.append(callback)

    def emit_quote_to_banner(self, symbol: str, price: float, change_pct: float = 0.0) -> None:
        for cb in self._banner_callbacks:
            try:
                cb(symbol, price, change_pct)
            except Exception:
                pass
    
    async def _update_indicators(self, symbol: str):
        """Update technical indicators for a symbol"""
        if len(self.data_cache[symbol]) < 20:  # Need minimum data for indicators
            return
        
        # Get recent prices
        recent_data = self.data_cache[symbol][-100:]  # Last 100 data points
        prices = [d.price for d in recent_data]
        
        # Calculate moving averages
        if len(prices) >= 20:
            ma20 = sum(prices[-20:]) / 20
            self.indicators[symbol]['MA20'] = ma20
        
        if len(prices) >= 50:
            ma50 = sum(prices[-50:]) / 50
            self.indicators[symbol]['MA50'] = ma50
        
        # Calculate RSI (simplified)
        if len(prices) >= 14:
            price_changes = [prices[i] - prices[i-1] for i in range(1, len(prices))]
            gains = [change for change in price_changes if change > 0]
            losses = [abs(change) for change in price_changes if change < 0]
            
            if gains and losses:
                avg_gain = sum(gains[-14:]) / 14
                avg_loss = sum(losses[-14:]) / 14
                
                if avg_loss > 0:
                    rs = avg_gain / avg_loss
                    rsi = 100 - (100 / (1 + rs))
                    self.indicators[symbol]['RSI'] = rsi
    
    async def _check_alerts(self, symbol: str, data: MarketData):
        """Check for price alerts"""
        for alert in self.alerts:
            if alert['symbol'] == symbol and alert['active']:
                if alert['type'] == 'price_above' and data.price >= alert['threshold']:
                    await self._trigger_alert(alert, data)
                elif alert['type'] == 'price_below' and data.price <= alert['threshold']:
                    await self._trigger_alert(alert, data)
                elif alert['type'] == 'volume_spike' and data.volume >= alert['threshold']:
                    await self._trigger_alert(alert, data)
    
    async def _trigger_alert(self, alert: Dict[str, Any], data: MarketData):
        """Trigger an alert"""
        alert_message = {
            'alert_id': alert['id'],
            'symbol': alert['symbol'],
            'type': alert['type'],
            'threshold': alert['threshold'],
            'current_value': data.price if 'price' in alert['type'] else data.volume,
            'timestamp': datetime.now(),
            'data': data
        }
        
        # Here you would send the alert to the user
        print(f"ALERT: {alert_message}")
    
    def add_price_alert(self, symbol: str, alert_type: str, threshold: float):
        """Add a price alert"""
        alert = {
            'id': len(self.alerts) + 1,
            'symbol': symbol,
            'type': alert_type,
            'threshold': threshold,
            'active': True,
            'created_at': datetime.now()
        }
        
        self.alerts.append(alert)
        return alert['id']
    
    def remove_alert(self, alert_id: int):
        """Remove an alert"""
        for alert in self.alerts:
            if alert['id'] == alert_id:
                alert['active'] = False
                break
    
    def get_latest_price(self, symbol: str) -> Optional[float]:
        """Get the latest price for a symbol"""
        if symbol in self.data_cache and self.data_cache[symbol]:
            return self.data_cache[symbol][-1].price
        return None
    
    def get_price_history(self, symbol: str, limit: int = 100) -> List[MarketData]:
        """Get price history for a symbol"""
        if symbol in self.data_cache:
            return self.data_cache[symbol][-limit:]
        return []
    
    def get_indicators(self, symbol: str) -> Dict[str, float]:
        """Get technical indicators for a symbol"""
        return self.indicators.get(symbol, {})
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get all active alerts"""
        return [alert for alert in self.alerts if alert['active']]
    
    async def start_monitoring(self, symbols: List[str], exchanges: List[str]):
        """Start monitoring symbols on exchanges"""
        for exchange in exchanges:
            await self.ws_manager.connect_to_exchange(exchange, symbols)
    
    async def stop_monitoring(self):
        """Stop all monitoring"""
        await self.ws_manager.disconnect_all()
