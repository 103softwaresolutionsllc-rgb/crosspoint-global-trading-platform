"""
Real-Time Trading Module for Fincept Terminal
16 broker integrations with WebSocket support and algorithmic trading
"""

from .websocket import WebSocketManager, RealTimeDataFeed
from .execution import OrderExecutor, TradingEngine
from .brokers.base import BaseBroker
from .brokers.ibkr import InteractiveBrokersBroker
from .brokers.alpaca import AlpacaBroker

__all__ = [
    "WebSocketManager",
    "RealTimeDataFeed",
    "OrderExecutor", 
    "TradingEngine",
    "BaseBroker",
    "InteractiveBrokersBroker",
    "AlpacaBroker",
]
