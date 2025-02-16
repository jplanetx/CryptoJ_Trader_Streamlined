
"""
Position Tracking Module
Implements basic position tracking functionality.
"""

from decimal import Decimal
from typing import Dict, Optional

class PositionTracker:
    def __init__(self):
        self.positions = {}  # Tracks current positions, keys are trading pairs, values are dicts with 'quantity' and 'entry_price'

    def update_position(self, symbol: str, side: str, size: Decimal, price: Decimal):
        """
        Updates the position tracking based on the trade.
        Args:
            symbol: The trading pair
            side: 'buy' or 'sell'
            size: The size of the trade
            price: The price at which the trade was executed.
        """
        if side == 'buy':
            if symbol not in self.positions:
                self.positions[symbol] = {'quantity': size, 'entry_price': price}
            else:
              current_position = self.positions[symbol]
              new_quantity = current_position['quantity'] + size
              new_entry_price = (current_position['quantity'] * current_position['entry_price'] + size * price) / new_quantity
              self.positions[symbol] = {'quantity': new_quantity, 'entry_price': new_entry_price}
        elif side == 'sell':
            if symbol not in self.positions:
                raise ValueError("No position exists")
            current_position = self.positions[symbol]
            if size > current_position['quantity']:
                raise ValueError("Insufficient position size")
            new_quantity = current_position['quantity'] - size
            if new_quantity == 0:
                del self.positions[symbol]
            else:
              self.positions[symbol]['quantity'] = new_quantity

    def get_position(self, symbol: str) -> Optional[Dict]:
        """
        Returns the current position for a symbol or None if no position
        """
        return self.positions.get(symbol)

