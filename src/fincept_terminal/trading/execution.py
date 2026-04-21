"""
Trading Execution Engine for Fincept Terminal
Advanced order execution with risk management and algorithmic trading
"""

import asyncio
import uuid
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import logging
import json

from .websocket import MarketData, TradeData, RealTimeDataFeed
from .brokers.base import BaseBroker


class OrderType(Enum):
    """Order types"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    TRAILING_STOP = "trailing_stop"


class OrderSide(Enum):
    """Order sides"""
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    """Order status"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIAL_FILLED = "partial_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class Order:
    """Order structure"""
    id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: str = "GTC"  # GTC, IOC, FOK, DAY
    created_at: datetime = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: float = 0.0
    average_fill_price: float = 0.0
    fills: List[Dict[str, Any]] = None
    broker: Optional[str] = None
    algorithm: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.fills is None:
            self.fills = []


@dataclass
class Position:
    """Position structure"""
    symbol: str
    quantity: float
    average_price: float
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    last_price: float = 0.0
    updated_at: datetime = None
    
    def __post_init__(self):
        if self.updated_at is None:
            self.updated_at = datetime.now()


@dataclass
class RiskLimits:
    """Risk management limits"""
    max_position_size: float = 100000.0
    max_daily_loss: float = 10000.0
    max_order_size: float = 50000.0
    max_leverage: float = 3.0
    min_account_balance: float = 25000.0


class OrderExecutor:
    """
    Advanced order execution engine with risk management.
    
    Features:
    - Multiple order types
    - Risk management
    - Position tracking
    - Order routing
    - Algorithmic execution
    - Performance analytics
    """
    
    def __init__(self, data_feed: RealTimeDataFeed, risk_limits: RiskLimits = None):
        self.data_feed = data_feed
        self.risk_limits = risk_limits or RiskLimits()
        self.orders: Dict[str, Order] = {}
        self.positions: Dict[str, Position] = {}
        self.brokers: Dict[str, BaseBroker] = {}
        self.order_handlers: List[Callable] = []
        self.position_handlers: List[Callable] = []
        self.logger = logging.getLogger(__name__)
        
        # Performance tracking
        self.daily_pnl = 0.0
        self.total_trades = 0
        self.win_rate = 0.0
        self.sharpe_ratio = 0.0
        
        # Risk tracking
        self.daily_trades = 0
        self.daily_loss = 0.0
        self.current_positions_value = 0.0
        
    def add_broker(self, name: str, broker: BaseBroker):
        """Add a broker connection"""
        self.brokers[name] = broker
        
    def add_order_handler(self, handler: Callable):
        """Add order status handler"""
        self.order_handlers.append(handler)
        
    def add_position_handler(self, handler: Callable):
        """Add position update handler"""
        self.position_handlers.append(handler)
    
    async def submit_order(self, order: Order, broker_name: str = None) -> str:
        """
        Submit an order for execution
        
        Args:
            order: Order to submit
            broker_name: Broker to use (auto-select if None)
            
        Returns:
            Order ID
        """
        try:
            # Validate order
            if not await self._validate_order(order):
                order.status = OrderStatus.REJECTED
                return order.id
            
            # Select broker
            if broker_name is None:
                broker_name = await self._select_broker(order)
            
            if broker_name not in self.brokers:
                raise ValueError(f"Broker {broker_name} not available")
            
            # Set broker
            order.broker = broker_name
            order.status = OrderStatus.SUBMITTED
            
            # Store order
            self.orders[order.id] = order
            
            # Submit to broker
            broker = self.brokers[broker_name]
            await broker.submit_order(order)
            
            # Notify handlers
            await self._notify_order_handlers(order)
            
            self.logger.info(f"Order submitted: {order.id}")
            return order.id
            
        except Exception as e:
            self.logger.error(f"Order submission failed: {e}")
            order.status = OrderStatus.REJECTED
            return order.id
    
    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an order
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            True if successful
        """
        try:
            if order_id not in self.orders:
                return False
            
            order = self.orders[order_id]
            
            if order.status not in [OrderStatus.SUBMITTED, OrderStatus.PARTIAL_FILLED]:
                return False
            
            # Cancel with broker
            if order.broker and order.broker in self.brokers:
                broker = self.brokers[order.broker]
                success = await broker.cancel_order(order_id)
                
                if success:
                    order.status = OrderStatus.CANCELLED
                    await self._notify_order_handlers(order)
                    self.logger.info(f"Order cancelled: {order_id}")
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Order cancellation failed: {e}")
            return False
    
    async def _validate_order(self, order: Order) -> bool:
        """Validate order against risk limits"""
        try:
            # Check position size limit
            current_position = self.positions.get(order.symbol, Position(order.symbol, 0, 0))
            new_position_size = current_position.quantity
            
            if order.side == OrderSide.BUY:
                new_position_size += order.quantity
            else:
                new_position_size -= order.quantity
            
            position_value = abs(new_position_size) * self._get_current_price(order.symbol)
            
            if position_value > self.risk_limits.max_position_size:
                self.logger.warning(f"Position size limit exceeded: {position_value}")
                return False
            
            # Check order size limit
            order_value = order.quantity * (order.price or self._get_current_price(order.symbol))
            if order_value > self.risk_limits.max_order_size:
                self.logger.warning(f"Order size limit exceeded: {order_value}")
                return False
            
            # Check daily loss limit
            if self.daily_loss >= self.risk_limits.max_daily_loss:
                self.logger.warning(f"Daily loss limit exceeded: {self.daily_loss}")
                return False
            
            # Check minimum account balance
            total_position_value = sum(
                abs(pos.quantity) * self._get_current_price(pos.symbol)
                for pos in self.positions.values()
            )
            
            if total_position_value > self.risk_limits.max_leverage * self.risk_limits.min_account_balance:
                self.logger.warning(f"Leverage limit exceeded")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Order validation error: {e}")
            return False
    
    async def _select_broker(self, order: Order) -> str:
        """Select best broker for order"""
        # Simple selection logic - can be enhanced
        available_brokers = list(self.brokers.keys())
        
        if not available_brokers:
            raise ValueError("No brokers available")
        
        # Select first available broker (can be enhanced with routing logic)
        return available_brokers[0]
    
    def _get_current_price(self, symbol: str) -> float:
        """Get current price for symbol"""
        return self.data_feed.get_latest_price(symbol) or 0.0
    
    async def handle_fill(self, order_id: str, fill_price: float, fill_quantity: float):
        """
        Handle order fill
        
        Args:
            order_id: Order ID
            fill_price: Fill price
            fill_quantity: Fill quantity
        """
        try:
            if order_id not in self.orders:
                return
            
            order = self.orders[order_id]
            
            # Add fill
            fill = {
                'price': fill_price,
                'quantity': fill_quantity,
                'timestamp': datetime.now(),
                'commission': 0.0  # Would be calculated by broker
            }
            order.fills.append(fill)
            
            # Update order
            order.filled_quantity += fill_quantity
            order.average_fill_price = (
                sum(f['price'] * f['quantity'] for f in order.fills) /
                order.filled_quantity
            )
            
            # Update position
            await self._update_position(order, fill_price, fill_quantity)
            
            # Update status
            if order.filled_quantity >= order.quantity:
                order.status = OrderStatus.FILLED
            else:
                order.status = OrderStatus.PARTIAL_FILLED
            
            # Update performance metrics
            await self._update_performance_metrics(order, fill_price, fill_quantity)
            
            # Notify handlers
            await self._notify_order_handlers(order)
            await self._notify_position_handlers(order.symbol)
            
            self.logger.info(f"Order filled: {order_id}, {fill_quantity}@{fill_price}")
            
        except Exception as e:
            self.logger.error(f"Fill handling error: {e}")
    
    async def _update_position(self, order: Order, fill_price: float, fill_quantity: float):
        """Update position after fill"""
        symbol = order.symbol
        
        if symbol not in self.positions:
            self.positions[symbol] = Position(symbol, 0, 0)
        
        position = self.positions[symbol]
        
        if order.side == OrderSide.BUY:
            # Add to position
            total_cost = (position.quantity * position.average_price) + (fill_quantity * fill_price)
            total_quantity = position.quantity + fill_quantity
            
            position.quantity = total_quantity
            position.average_price = total_cost / total_quantity if total_quantity > 0 else 0
            
        else:
            # Reduce position
            if position.quantity >= fill_quantity:
                # Calculate realized PnL
                realized_pnl = (fill_price - position.average_price) * fill_quantity
                position.realized_pnl += realized_pnl
                
                # Update position
                position.quantity -= fill_quantity
                
                # If position is closed, reset average price
                if position.quantity == 0:
                    position.average_price = 0
            else:
                # Short position (not implemented in this example)
                pass
        
        # Update unrealized PnL
        current_price = self._get_current_price(symbol)
        if position.quantity != 0:
            position.unrealized_pnl = (current_price - position.average_price) * position.quantity
        
        position.last_price = current_price
        position.updated_at = datetime.now()
    
    async def _update_performance_metrics(self, order: Order, fill_price: float, fill_quantity: float):
        """Update performance metrics"""
        self.total_trades += 1
        self.daily_trades += 1
        
        # Update daily PnL
        symbol = order.symbol
        if symbol in self.positions:
            position = self.positions[symbol]
            self.daily_pnl += position.realized_pnl
            
            if position.realized_pnl < 0:
                self.daily_loss += abs(position.realized_pnl)
    
    async def _notify_order_handlers(self, order: Order):
        """Notify order handlers"""
        for handler in self.order_handlers:
            try:
                await handler(order)
            except Exception as e:
                self.logger.error(f"Order handler error: {e}")
    
    async def _notify_position_handlers(self, symbol: str):
        """Notify position handlers"""
        if symbol in self.positions:
            position = self.positions[symbol]
            for handler in self.position_handlers:
                try:
                    await handler(position)
                except Exception as e:
                    self.logger.error(f"Position handler error: {e}")
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID"""
        return self.orders.get(order_id)
    
    def get_orders(self, status: OrderStatus = None) -> List[Order]:
        """Get orders by status"""
        orders = list(self.orders.values())
        
        if status:
            orders = [order for order in orders if order.status == status]
        
        return orders
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position by symbol"""
        return self.positions.get(symbol)
    
    def get_positions(self) -> Dict[str, Position]:
        """Get all positions"""
        return self.positions.copy()
    
    def get_portfolio_value(self) -> float:
        """Get total portfolio value"""
        total_value = 0.0
        
        for position in self.positions.values():
            if position.quantity != 0:
                position_value = position.quantity * position.last_price
                total_value += position_value
        
        return total_value
    
    def get_total_pnl(self) -> float:
        """Get total PnL"""
        total_pnl = 0.0
        
        for position in self.positions.values():
            total_pnl += position.realized_pnl + position.unrealized_pnl
        
        return total_pnl
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        return {
            'total_trades': self.total_trades,
            'daily_trades': self.daily_trades,
            'daily_pnl': self.daily_pnl,
            'daily_loss': self.daily_loss,
            'total_pnl': self.get_total_pnl(),
            'portfolio_value': self.get_portfolio_value(),
            'win_rate': self.win_rate,
            'sharpe_ratio': self.sharpe_ratio,
            'active_orders': len([o for o in self.orders.values() if o.status in [OrderStatus.SUBMITTED, OrderStatus.PARTIAL_FILLED]]),
            'total_positions': len([p for p in self.positions.values() if p.quantity != 0]),
        }


class TradingEngine:
    """
    Main trading engine coordinating all trading activities.
    
    Features:
    - Order management
    - Risk management
    - Algorithmic trading
    - Performance tracking
    - Multi-broker support
    """
    
    def __init__(self, data_feed: RealTimeDataFeed, risk_limits: RiskLimits = None):
        self.data_feed = data_feed
        self.executor = OrderExecutor(data_feed, risk_limits)
        self.algorithms: Dict[str, Any] = {}
        self.is_running = False
        self.logger = logging.getLogger(__name__)
        
        # Register handlers
        self.executor.add_order_handler(self._handle_order_update)
        self.executor.add_position_handler(self._handle_position_update)
    
    async def start(self):
        """Start the trading engine"""
        self.is_running = True
        self.logger.info("Trading engine started")
        
        # Start algorithm loops
        for algo_name, algorithm in self.algorithms.items():
            asyncio.create_task(self._run_algorithm(algo_name, algorithm))
    
    async def stop(self):
        """Stop the trading engine"""
        self.is_running = False
        
        # Cancel all open orders
        await self.cancel_all_orders()
        
        self.logger.info("Trading engine stopped")
    
    def add_algorithm(self, name: str, algorithm):
        """Add a trading algorithm"""
        self.algorithms[name] = algorithm
    
    def remove_algorithm(self, name: str):
        """Remove a trading algorithm"""
        if name in self.algorithms:
            del self.algorithms[name]
    
    async def submit_order(self, symbol: str, side: str, order_type: str,
                          quantity: float, price: float = None, **kwargs) -> str:
        """Submit an order"""
        order = Order(
            id=str(uuid.uuid4()),
            symbol=symbol,
            side=OrderSide(side),
            order_type=OrderType(order_type),
            quantity=quantity,
            price=price,
            **kwargs
        )
        
        return await self.executor.submit_order(order)
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        return await self.executor.cancel_order(order_id)
    
    async def cancel_all_orders(self):
        """Cancel all open orders"""
        open_orders = self.executor.get_orders(OrderStatus.SUBMITTED) + \
                     self.executor.get_orders(OrderStatus.PARTIAL_FILLED)
        
        for order in open_orders:
            await self.executor.cancel_order(order.id)
    
    async def _run_algorithm(self, algo_name: str, algorithm):
        """Run a trading algorithm"""
        while self.is_running:
            try:
                await algorithm.execute(self)
                await asyncio.sleep(1)  # Algorithm execution frequency
            except Exception as e:
                self.logger.error(f"Algorithm {algo_name} error: {e}")
                await asyncio.sleep(5)  # Wait before retrying
    
    async def _handle_order_update(self, order: Order):
        """Handle order updates"""
        # Log order updates
        self.logger.info(f"Order update: {order.id} - {order.status.value}")
    
    async def _handle_position_update(self, position: Position):
        """Handle position updates"""
        # Update position PnL
        current_price = self.data_feed.get_latest_price(position.symbol)
        if current_price and position.quantity != 0:
            position.unrealized_pnl = (current_price - position.average_price) * position.quantity
            position.last_price = current_price
            position.updated_at = datetime.now()
    
    def get_status(self) -> Dict[str, Any]:
        """Get trading engine status"""
        return {
            'is_running': self.is_running,
            'algorithms': list(self.algorithms.keys()),
            'performance': self.executor.get_performance_summary(),
            'orders': {
                'total': len(self.executor.orders),
                'active': len([o for o in self.executor.orders.values() if o.status in [OrderStatus.SUBMITTED, OrderStatus.PARTIAL_FILLED]]),
                'pending': len(self.executor.get_orders(OrderStatus.PENDING)),
                'filled': len(self.executor.get_orders(OrderStatus.FILLED)),
            },
            'positions': {
                'total': len(self.executor.positions),
                'active': len([p for p in self.executor.positions.values() if p.quantity != 0]),
            }
        }
