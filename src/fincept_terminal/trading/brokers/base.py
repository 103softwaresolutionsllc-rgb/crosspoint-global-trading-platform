"""
Base Broker Interface for Fincept Terminal
Abstract base class for all broker integrations
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import asyncio

from ..execution import Order, OrderStatus


@dataclass
class BrokerAccount:
    """Broker account information"""
    account_id: str
    broker_name: str
    cash_balance: float
    portfolio_value: float
    buying_power: float
    margin_available: float
    day_trades: int
    pattern_day_trader: bool
    last_updated: datetime


@dataclass
class BrokerPosition:
    """Broker position information"""
    symbol: str
    quantity: float
    average_price: float
    market_value: float
    unrealized_pnl: float
    side: str  # 'long' or 'short'


class BaseBroker(ABC):
    """
    Abstract base class for broker integrations.
    
    All broker implementations must inherit from this class
    and implement the required methods.
    """
    
    def __init__(self, name: str):
        self.name = name
        self.is_connected = False
        self.account_info: Optional[BrokerAccount] = None
        
    @abstractmethod
    async def connect(self, credentials: Dict[str, str]) -> bool:
        """
        Connect to the broker API
        
        Args:
            credentials: Dictionary with API credentials
            
        Returns:
            True if connection successful
        """
        pass
    
    @abstractmethod
    async def disconnect(self):
        """Disconnect from the broker API"""
        pass
    
    @abstractmethod
    async def submit_order(self, order: Order) -> bool:
        """
        Submit an order to the broker
        
        Args:
            order: Order to submit
            
        Returns:
            True if submission successful
        """
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an order
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            True if cancellation successful
        """
        pass
    
    @abstractmethod
    async def get_order_status(self, order_id: str) -> OrderStatus:
        """
        Get order status
        
        Args:
            order_id: Order ID
            
        Returns:
            Current order status
        """
        pass
    
    @abstractmethod
    async def get_account_info(self) -> BrokerAccount:
        """
        Get account information
        
        Returns:
            Account information
        """
        pass
    
    @abstractmethod
    async def get_positions(self) -> List[BrokerPosition]:
        """
        Get all positions
        
        Returns:
            List of positions
        """
        pass
    
    @abstractmethod
    async def get_open_orders(self) -> List[Order]:
        """
        Get all open orders
        
        Returns:
            List of open orders
        """
        pass
    
    async def get_market_data(self, symbol: str) -> Dict[str, Any]:
        """
        Get market data for a symbol (optional implementation)
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Market data dictionary
        """
        # Default implementation - can be overridden
        return {}
    
    async def get_order_history(self, limit: int = 100) -> List[Order]:
        """
        Get order history (optional implementation)
        
        Args:
            limit: Maximum number of orders to return
            
        Returns:
            List of historical orders
        """
        # Default implementation - can be overridden
        return []
    
    def validate_credentials(self, credentials: Dict[str, str]) -> bool:
        """
        Validate API credentials (optional implementation)
        
        Args:
            credentials: API credentials
            
        Returns:
            True if credentials appear valid
        """
        # Default implementation - can be overridden
        return True
    
    def get_supported_order_types(self) -> List[str]:
        """
        Get supported order types
        
        Returns:
            List of supported order types
        """
        return ['market', 'limit', 'stop', 'stop_limit']
    
    def get_supported_assets(self) -> List[str]:
        """
        Get supported asset classes
        
        Returns:
            List of supported asset classes
        """
        return ['stocks', 'etfs', 'options']
    
    async def test_connection(self) -> bool:
        """
        Test broker connection
        
        Returns:
            True if connection is working
        """
        try:
            account_info = await self.get_account_info()
            return account_info is not None
        except Exception:
            return False
