"""
Order Execution Module
Implements the OrderExecution base class and OrderExecutor class responsible for executing trading orders.
"""

import logging
from decimal import Decimal
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class OrderExecutor:
    def __init__(self, *args, **kwargs):
        # Extract trading_pair from positional or keyword argument (avoids duplicate values)
        trading_pair = args[0] if args else None
        if "trading_pair" in kwargs:
            trading_pair = kwargs.pop("trading_pair")
        if not trading_pair:
            raise ValueError("Trading pair must be specified in the constructor")
        self.trading_pair = trading_pair
        self.default_fill_price = Decimal("50000.0")
        self.positions: Dict[str, Decimal] = {}

    def get_position(self, symbol: str) -> Decimal:
        """Returns the current position for a given symbol."""
        return self.positions.get(symbol, Decimal("0"))

    def initialize_position(self, symbol: str, quantity: Decimal, price: Decimal):
        """Initializes the position for a given symbol."""
        self.positions[symbol] = quantity

    async def execute_order(self, order: Dict = None, *, order_data: Dict = None) -> Dict:
        if order_data is not None:
            order = order_data
        if order is None:
            raise ValueError("No order provided")
        side = order.get('side', '').lower()
        if side not in ['buy', 'sell']:
            raise ValueError("Invalid order side")
        try:
            quantity = Decimal(str(order.get('quantity', '0')))
        except decimal.InvalidOperation:
            raise ValueError("Invalid quantity value")
        fill_price = self.default_fill_price
        if side == 'sell' and self.get_position(self.trading_pair) == 0:
            raise ValueError("No position exists")
        result = {
            'order_id': 'paper_trade',
            'product_id': self.trading_pair,
            'side': side,
            'type': order.get('type', 'market'),
            'size': str(quantity),
            'price': str(fill_price),
            'status': 'success'
        }
        logger.info(f"Executed paper trade order: {result}")
        return result

    async def create_order(self,
                           symbol: str,
                           side: str,
                           quantity: Decimal,
                           price: Optional[Decimal] = None,
                           order_type: str = 'market') -> Dict:
        order = {
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'type': order_type
        }
        if order_type == 'limit' and price is None:
            raise ValueError("Limit price required")
        if price is not None:
            order['price'] = price
        return await self.execute_order(order=order)

# Top-level async function for tests
async def execute_order(order: Dict) -> Dict:
    executor = OrderExecutor(trading_pair=order.get('symbol', "BTC-USD"))
    return await executor.execute_order(order=order)
