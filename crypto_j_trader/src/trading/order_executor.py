"""Handles order execution and position tracking"""
import logging
from decimal import Decimal
from typing import Dict, Optional, Union
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class Position:
    """Represents a trading position"""
    symbol: str
    quantity: Decimal
    entry_price: Decimal
    timestamp: datetime

class OrderExecutor:
    """Handles order execution and position tracking"""
    
    def __init__(self, trading_bot=None, trading_pair=None, *args, **kwargs):
        from .trading_core import validate_trading_pair
        
        self.trading_bot = trading_bot
        
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
        if not validate_trading_pair(self.trading_pair):
            raise ValueError(f"Invalid trading pair format: {self.trading_pair}")
            
        self.default_fill_price = Decimal("50000.0")
        self.positions = {}
        self.orders = {}
        self._order_counter = 1000
        self._mock_mode = kwargs.get('mock_mode', False)

    def get_position(self, symbol: str) -> Dict:
        """Get current position details for a symbol."""
        pos = self.positions.get(symbol, {
            'size': Decimal('0'),
            'entry_price': Decimal('0'),
            'current_price': Decimal('0'),
            'unrealized_pnl': Decimal('0'),
            'stop_loss': Decimal('0')
        })
        return pos

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
                return {'status': 'error', 'message': 'Invalid size'}
            if price_dec <= 0:
                return {'status': 'error', 'message': 'Invalid price'}
            
            # Get current position
            position = self.get_position(symbol)
            
            # Update position based on order
            side_lower = side.lower() if isinstance(side, str) else side['side'].lower()
            if side_lower == 'buy':
                new_size = position['size'] + size_dec
                new_price = position['entry_price'] if position['size'] > 0 else price_dec
            else:
                if position['size'] < size_dec:
                    return {'status': 'error', 'message': 'Insufficient position size'}
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
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Order execution error: {str(e)}")
            return {
                'status': 'error',
                'message': str(e),
                'symbol': symbol
            }

    def _generate_order_id(self) -> str:
        """Generate a unique order ID"""
        self._order_id_counter += 1
        return f"order_{self._order_id_counter}"
        
    async def create_order(self, side, quantity, price, symbol):
        """Create a new order with position tracking"""
        try:
            # Input validation
            if not symbol or not isinstance(symbol, str):
                raise ValueError("Invalid symbol")
            if not quantity or quantity <= 0:
                raise ValueError("Invalid quantity")
            if price is not None and price <= 0:
                raise ValueError("Invalid price")
            if side not in ['buy', 'sell']:
                raise ValueError("Invalid side - must be 'buy' or 'sell'")
                
            # Generate order ID and create order
            order_id = self._generate_order_id()
            order = {
                "status": "success",
                "order_id": order_id,
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "price": price,
                "timestamp": datetime.now().isoformat()
            }
            
            # Store order
            self.orders[order_id] = order
            
            # Update position
            quantity_dec = Decimal(str(quantity))
            price_dec = Decimal(str(price)) if price else Decimal('0')
            
            if side == 'buy':
                if symbol in self.positions:
                    # Update existing position
                    pos = self.positions[symbol]
                    new_quantity = pos.quantity + quantity_dec
                    avg_price = ((pos.quantity * pos.entry_price) + (quantity_dec * price_dec)) / new_quantity
                    self.positions[symbol] = Position(symbol, new_quantity, avg_price, datetime.now())
                else:
                    # Create new position
                    self.positions[symbol] = Position(symbol, quantity_dec, price_dec, datetime.now())
            else:  # sell
                if symbol not in self.positions:
                    raise ValueError(f"No position exists for {symbol}")
                pos = self.positions[symbol]
                if quantity_dec > pos.quantity:
                    raise ValueError(f"Insufficient position size: {pos.quantity} < {quantity_dec}")
                # Update position
                new_quantity = pos.quantity - quantity_dec
                if new_quantity == 0:
                    del self.positions[symbol]
                else:
                    self.positions[symbol] = Position(symbol, new_quantity, pos.entry_price, datetime.now())
            
            logger.info(f"Order created successfully: {order_id}")
            return {
                'status': 'success',
                'order_id': 'mock-order-id',
                'entry_price': price,
                'quantity': quantity,
                'stop_loss': price * 0.95  # simple stop loss calc
            }
            
        except Exception as e:
            logger.error(f"Order creation failed: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
            
    def get_order_status(self, order_id: str) -> Dict:
        """Get status of an order with detailed information"""
        if order_id not in self.orders:
            return {
                "status": "error",
                "message": f"Order not found: {order_id}"
            }
            
        order = self.orders[order_id]
        return {
            "status": "filled",  # Simulate instant fill for MVP
            "order_id": order_id,
            "symbol": order["symbol"],
            "side": order["side"],
            "filled_quantity": order["quantity"],
            "remaining_quantity": 0.0,
            "price": order["price"],
            "timestamp": order["timestamp"]
        }
        
    def cancel_order(self, order_id: str) -> Dict:
        """Cancel an existing order"""
        if order_id not in self.orders:
            return {
                "status": "error",
                "message": f"Order not found: {order_id}"
            }
        
        # Remove order and return success
        order = self.orders.pop(order_id)
        return {
            "status": "success",
            "order_id": order_id,
            "message": "Order cancelled",
            "symbol": order["symbol"],
            "timestamp": datetime.now().isoformat()
        }
        
    def get_position(self, symbol: str) -> Optional[Dict]:
        """Get current position for a symbol"""
        if symbol not in self.positions:
            return None
            
        pos = self.positions[symbol]
        return {
            "symbol": pos.symbol,
            "quantity": float(pos.quantity),
            "entry_price": float(pos.entry_price),
            "stop_loss": float(pos.entry_price * Decimal("0.95") if pos.quantity > 0 else 0),
            "timestamp": pos.timestamp.isoformat()
        }