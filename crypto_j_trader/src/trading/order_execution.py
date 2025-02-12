"""
Order Execution Module
Implements the OrderExecution base class and OrderExecutor class responsible for executing trading orders.
"""

import logging
from decimal import Decimal, InvalidOperation
from typing import Dict, Optional, Union, Any
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class Position:
    """Represents a trading position"""
    symbol: str
    size: Decimal
    entry_price: Decimal
    timestamp: datetime

class OrderExecutor:
    """Handles order execution and position tracking"""
    
    def __init__(self, *args, **kwargs):
        from .trading_core import validate_trading_pair
        # Extract trading_pair from positional or keyword argument
        self.trading_pair = None
        if args:
            if isinstance(args[0], str):
                self.trading_pair = args[0]
            elif hasattr(args[0], 'trading_pair'):
                self.trading_pair = args[0].trading_pair
        if "trading_pair" in kwargs:
            self.trading_pair = kwargs.pop("trading_pair")
            
        if self.trading_pair and not validate_trading_pair(self.trading_pair):
            raise ValueError(f"Invalid trading pair format: {self.trading_pair}")
        if not self.trading_pair:
            raise ValueError("Trading pair must be specified in the constructor")
            
        self.default_fill_price = Decimal("50000.0")
        self.positions: Dict[str, Position] = {}
        self.orders: Dict[str, Dict[str, Any]] = {}
        self._order_counter = 1000
        self._mock_mode = kwargs.get('mock_mode', False)
        self._position_size = Decimal('0')

    def get_position(self, symbol: str) -> Dict:
        """Returns the current position for a given symbol."""
        if self._mock_mode:
            return {
                "size": float(self._position_size),
                "entry_price": float(self.default_fill_price if self._position_size != 0 else 0),
                "stop_loss": float(self.default_fill_price * Decimal("0.95") if self._position_size > 0 else 0)
            }
            
        pos = self.positions.get(symbol)
        if not pos:
            return {
                "size": 0.0,
                "entry_price": 0.0,
                "stop_loss": 0.0
            }
        
        return {
            "size": float(pos.size),
            "entry_price": float(pos.entry_price),
            "stop_loss": float(pos.entry_price * Decimal("0.95") if pos.size > 0 else 0)
        }

    def _validate_order_params(self, side: str, size: Union[int, float, Decimal, str], 
                             price: Union[int, float, Decimal, str], order_type: str = None) -> None:
        """Validate order parameters."""
        try:
            if isinstance(size, str):
                raise ValueError("Invalid literal for Decimal")
            size_dec = Decimal(str(size))
            if size_dec <= 0:
                raise ValueError("Invalid size")
        except (InvalidOperation, TypeError):
            raise ValueError("Invalid literal for Decimal")

        try:
            price_dec = Decimal(str(price))
            if price_dec <= 0:
                raise ValueError("Invalid price")
        except (InvalidOperation, TypeError):
            raise ValueError("Invalid literal for Decimal")

        if not isinstance(side, str) or side.lower() not in ('buy', 'sell'):
            raise ValueError("Invalid order side")

        if order_type == 'limit' and not price:
            raise ValueError("Limit price required")

    async def execute_order(self, side: Union[str, Dict], size: Optional[float] = None, 
                          price: Optional[float] = None, symbol: Optional[str] = None) -> Dict:
        """Execute a trade order. Supports both dict and parameter-based calls."""
        try:
            # Handle dict-style calls
            if isinstance(side, dict):
                order = side
                symbol = order.get('symbol', self.trading_pair)
                side = order['side']
                size = order.get('quantity', 0)
                price = order.get('price', self.default_fill_price)
                order_type = order.get('type', 'market')

                # Handle limit orders without price
                if order_type == 'limit' and 'price' not in order:
                    raise ValueError("Limit price required")
            else:
                symbol = symbol or self.trading_pair
                order_type = 'market'

            # Validate parameters
            self._validate_order_params(side, size, price, order_type)

            size_dec = Decimal(str(size))
            price_dec = Decimal(str(price))

            # Update position based on order
            side = side.lower() if isinstance(side, str) else side['side'].lower()
            if side == 'buy':
                self._position_size += size_dec
            else:
                if self._position_size < size_dec:
                    raise ValueError("Insufficient position size")
                self._position_size -= size_dec

            # Return consistent filled status
            return {
                'status': 'filled',
                'order_id': 'mock-order-id' if self._mock_mode else f"order_{self._order_counter}",
                'symbol': symbol,
                'side': side,
                'size': str(size_dec),
                'price': str(price_dec),
                'type': order_type
            }

        except ValueError as e:
            raise
        except Exception as e:
            logger.error(f"Order execution failed: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }

    async def create_order(self, symbol: str, side: str, quantity: Union[Decimal, float], 
                          price: Optional[Union[Decimal, float]] = None, 
                          order_type: str = 'market') -> Dict:
        """Create and execute an order."""
        return await self.execute_order(
            side=side,
            size=float(quantity),
            price=float(price) if price else float(self.default_fill_price),
            symbol=symbol
        )

# Standalone function for backward compatibility
async def execute_order(order: Dict = None, *, order_data: Dict = None) -> Dict:
    """Execute an order using the OrderExecutor."""
    order = order or order_data
    if not order:
        raise ValueError("No order data provided")
    executor = OrderExecutor(trading_pair=order.get('symbol', "BTC-USD"), mock_mode=True)
    return await executor.execute_order(order)
