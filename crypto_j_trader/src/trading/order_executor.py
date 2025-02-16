"""Handles order execution and position tracking"""
import logging
from decimal import Decimal
from typing import Dict, Optional, Union, TypedDict, Literal
from dataclasses import dataclass
from datetime import datetime

from .config_manager import ConfigManager

logger = logging.getLogger(__name__)

class OrderResponse(TypedDict):
    """Standard order response format"""
    status: Literal['filled', 'error', 'success']
    order_id: str
    symbol: str
    side: str
    size: str
    price: str
    type: str
    timestamp: str
    message: Optional[str]

class PositionInfo(TypedDict):
    """Standard position information format"""
    size: Decimal
    entry_price: Decimal
    unrealized_pnl: Decimal
    timestamp: datetime
    stop_loss: Decimal

@dataclass
class Position:
    """Represents a trading position"""
    symbol: str
    size: Decimal
    entry_price: Decimal
    timestamp: datetime = datetime.now()
    stop_loss: Optional[Decimal] = None

    def update_stop_loss(self, price: Decimal, stop_loss_pct: float = 0.05):
        """Update stop loss based on current price"""
        self.stop_loss = price * Decimal(str(1 - stop_loss_pct))

class OrderExecutor:
    """Handles order execution and position tracking"""
    
    def __init__(self, trading_bot=None, trading_pair=None, *args, **kwargs):
        self.config = ConfigManager()
        
        # Initialize counters and tracking variables first
        self._order_counter = 1000
        self._order_id_counter = 1000  # Add this line to fix the missing attribute
        
        # Extract trading_pair from parameters
        if trading_pair:
            self.trading_pair = trading_pair
        elif trading_bot and hasattr(trading_bot, 'trading_pair'):
            self.trading_pair = trading_bot.trading_pair
        elif args and isinstance(args[0], str):
            self.trading_pair = args[0]
        else:
            self.trading_pair = kwargs.get('trading_pair')
            
        if not self.trading_pair:
            raise ValueError("Trading pair must be specified in the constructor")
        if not self.config.validate_trading_pair(self.trading_pair):
            raise ValueError(f"Invalid trading pair format: {self.trading_pair}")
            
        # Initialize from config
        test_config = self.config.get_test_config()
        self.default_fill_price = Decimal(str(test_config.get('default_fill_price', '50000.0')))
        self.positions: Dict[str, Position] = {}
        self.orders: Dict[str, Dict] = {}
        self._mock_mode = kwargs.get('mock_mode', test_config.get('mock_mode', False))
        
        # Load risk parameters
        risk_config = self.config.get_risk_parameters()
        self.max_position_size = Decimal(str(risk_config.get('max_position_size', 5.0)))
        self.stop_loss_pct = float(risk_config.get('stop_loss_pct', 0.05))

    def get_position(self, symbol: str) -> PositionInfo:
        """Get current position details for a symbol."""
        if symbol not in self.positions:
            return {
                'size': Decimal('0'),
                'entry_price': Decimal('0'),
                'unrealized_pnl': Decimal('0'),
                'timestamp': datetime.now(),
                'stop_loss': Decimal('0')
            }
        pos = self.positions[symbol]
        return {
            "size": pos.size,
            "entry_price": pos.entry_price,
            "unrealized_pnl": Decimal('0'),  # Calculated in real implementation
            "timestamp": pos.timestamp,
            "stop_loss": pos.stop_loss or Decimal('0')
        }

    async def execute_order(self, side: Union[str, Dict], size: Optional[float] = None, 
                          price: Optional[float] = None, symbol: Optional[str] = None) -> OrderResponse:
        """Execute a trade order. Supports both dict and parameter-based calls."""
        try:
            # Handle dict-style calls
            if isinstance(side, dict):
                order = side
                symbol = order.get('symbol', self.trading_pair)
                side = order['side']
                size = order.get('quantity', 0)
                price = order.get('price', float(self.default_fill_price))
                order_type = order.get('type', 'market')
            else:
                symbol = symbol or self.trading_pair
                order_type = 'market'
                
            # Convert parameters to Decimal
            size_dec = Decimal(str(size))
            price_dec = Decimal(str(price))
            
            # Basic validation
            if size_dec <= 0:
                return self._create_error_response('Invalid size')
            if price_dec <= 0:
                return self._create_error_response('Invalid price')
            
            # Get current position
            position = self.get_position(symbol)
            
            # Update position based on order
            side_lower = side.lower() if isinstance(side, str) else side['side'].lower()
            if side_lower == 'buy':
                new_size = position['size'] + size_dec
                new_price = position['entry_price'] if position['size'] > 0 else price_dec
            else:
                if position['size'] < size_dec:
                    return self._create_error_response('Insufficient position size')
                new_size = position['size'] - size_dec
                new_price = position['entry_price']
            
            # Update position
            self.positions[symbol] = {
                'size': new_size,
                'entry_price': new_price,
                'current_price': price_dec,
                'unrealized_pnl': (price_dec - new_price) * new_size if new_size > 0 else Decimal('0'),
                'stop_loss': new_price * Decimal('0.95') if new_size > 0 else Decimal('0')
            }
            
            # Generate order response
            self._order_counter += 1
            order_id = f'mock-order-{self._order_counter}'
            return {
                'status': 'filled',
                'order_id': order_id,
                'symbol': symbol,
                'side': side_lower,
                'size': str(size_dec),
                'price': str(price_dec),
                'type': order_type,
                'timestamp': datetime.now().isoformat(),
                'message': None
            }

        except Exception as e:
            logger.error(f"Order execution error: {str(e)}")
            return self._create_error_response(str(e), symbol=symbol)

    def _generate_order_id(self) -> str:
        """Generate a unique order ID"""
        self._order_id_counter += 1
        return f"order_{self._order_id_counter}"
        
    async def create_order(self, symbol: str, side: str, quantity: Union[Decimal, float], 
                          price: Optional[Union[Decimal, float]] = None, 
                          order_type: str = 'market') -> OrderResponse:
        """Create and execute an order."""
        try:
            self._validate_order_input(side, quantity, price, symbol)
            order_id = self._generate_order_id()
            order = self._create_order_dict(order_id, side, quantity, price, symbol)
            self.orders[order_id] = order
            
            # Update position first to catch any position-related errors
            size_dec = Decimal(str(quantity))
            price_dec = Decimal(str(price)) if price else self.default_fill_price
            self._update_position(symbol, side, size_dec, price_dec)
            
            logger.info(f"Order created successfully: {order_id}")
            
            # Return success response with position details
            return {
                "status": "success",
                "order_id": order_id,
                "symbol": symbol,
                "side": side,
                "size": str(quantity),
                "price": str(price_dec),
                "type": order_type,
                "timestamp": datetime.now().isoformat(),
                "message": None
            }
            
        except Exception as e:
            logger.error(f"Order creation failed: {e}")
            return self._create_error_response(str(e))

    def _validate_order_input(self, side, quantity, price, symbol):
        """Validate the input parameters for creating an order."""
        if not symbol or not isinstance(symbol, str):
            raise ValueError("Invalid symbol")
        if not quantity or quantity <= 0:
            raise ValueError("Invalid quantity")
        if price is not None and price <= 0:
            raise ValueError("Invalid price")
        if side not in ['buy', 'sell']:
            raise ValueError("Invalid side - must be 'buy' or 'sell'")

    def _create_order_dict(self, order_id, side, size, price, symbol) -> OrderResponse:
        """Create the order dictionary."""
        return {
            "status": "success",
            "order_id": order_id,
            "symbol": symbol,
            "side": side,
            "size": str(size),  # Convert to string for consistent API
            "price": str(price),
            "type": "market",
            "timestamp": datetime.now().isoformat(),
            "message": None
        }

    def _create_error_response(self, message: str, order_id: str = "ERROR", symbol: Optional[str] = None) -> OrderResponse:
        """Create standardized error response"""
        return {
            "status": "error",
            "order_id": order_id,
            "symbol": symbol or "",
            "side": "",
            "size": "0",
            "price": "0",
            "type": "",
            "timestamp": datetime.now().isoformat(),
            "message": message
        }

    def _update_position(self, symbol: str, side: str, size: Decimal, price: Decimal) -> None:
        """Update position with new order"""
        current_position = self.positions.get(symbol)
        
        if side == 'buy':
            if current_position:
                # Update existing position
                new_size = current_position.size + size
                if new_size > self.max_position_size:
                    raise ValueError(f"Position size {new_size} would exceed maximum {self.max_position_size}")
                weighted_price = ((current_position.size * current_position.entry_price) + 
                                (size * price)) / new_size
                current_position.size = new_size
                current_position.entry_price = weighted_price
                current_position.update_stop_loss(price, self.stop_loss_pct)
            else:
                # Create new position
                if size > self.max_position_size:
                    raise ValueError(f"Position size {size} exceeds maximum {self.max_position_size}")
                position = Position(symbol=symbol, size=size, entry_price=price)
                position.update_stop_loss(price, self.stop_loss_pct)
                self.positions[symbol] = position
        else:  # sell
            if not current_position:
                raise ValueError(f"No position exists for {symbol}")
            if size > current_position.size:
                raise ValueError(f"Insufficient position size: {current_position.size} < {size}")
            
            new_size = current_position.size - size
            if new_size == 0:
                del self.positions[symbol]
            else:
                current_position.size = new_size
                current_position.update_stop_loss(price, self.stop_loss_pct)

    def _create_order_response(self, order_id, price, quantity) -> OrderResponse:
        """Create the response dictionary for the order."""
        return {
            'status': 'success',
            'order_id': order_id,
            'entry_price': price,
            'quantity': quantity,
            'stop_loss': price * Decimal('0.95')  # Convert stop loss factor to Decimal
        }
            
    def get_order_status(self, order_id: str) -> OrderResponse:
        """Get status of an order with detailed information"""
        if order_id not in self.orders:
            return self._create_error_response(f"Order not found: {order_id}")
            
        order = self.orders[order_id]
        return {
            "status": "filled",  # Simulate instant fill for MVP
            "order_id": order_id,
            "symbol": order["symbol"],
            "side": order["side"],
            "size": order["size"],  # Changed from quantity to size
            "price": str(order["price"]),
            "type": "market",
            "timestamp": order["timestamp"],
            "message": None
        }
        
    def cancel_order(self, order_id: str) -> OrderResponse:
        """Cancel an existing order"""
        if order_id not in self.orders:
            return self._create_error_response(f"Order not found: {order_id}")
        order = self.orders[order_id]
        # If order is filled or marked as success, simulate that it cannot be cancelled
        if order.get("status") in ("filled", "success"):
            return self._create_error_response("Order already filled")
        self.orders.pop(order_id)
        return {
            "status": "success",
            "order_id": order_id,
            "symbol": order["symbol"],
            "side": order["side"],
            "size": order["size"],  # Changed from quantity to size
            "price": str(order["price"]),
            "type": "market",
            "timestamp": datetime.now().isoformat(),
            "message": "Order cancelled"
        }
        
    async def get(self, order_id: str) -> OrderResponse:
        """
        Retrieves the details of a specific order.
        """
        # In a real implementation, this would interact with an exchange API.
        # This is a placeholder for the actual order retrieval logic.
        return {
            'order_id': order_id,
            'status': 'open',
            'symbol': '',
            'side': '',
            'size': '0',
            'price': '0',
            'type': '',
            'timestamp': datetime.now().isoformat(),
            'message': None
        }