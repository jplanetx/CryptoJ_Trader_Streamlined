"""Handles order execution and position tracking"""
import logging
from decimal import Decimal
from typing import Dict, Optional
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
    
    def __init__(self, api_key: str, base_url: str, timeout: int = 30):
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.positions: Dict[str, Position] = {}  # Track positions by symbol
        self.orders: Dict[str, Dict] = {}  # Track order history
        self._order_id_counter = 1000  # For generating unique order IDs
        
    def _generate_order_id(self) -> str:
        """Generate a unique order ID"""
        self._order_id_counter += 1
        return f"order_{self._order_id_counter}"
        
    def create_order(self, symbol: str, side: str, quantity: float, price: Optional[float] = None) -> Dict:
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
            return order
            
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
            "timestamp": pos.timestamp.isoformat()
        }