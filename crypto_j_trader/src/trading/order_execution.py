"""
Order Execution Module
Implements the OrderExecution base class and OrderExecutor class responsible for executing trading orders.
"""

import logging
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Dict, Optional
from coinbase.rest import RESTClient

# Configure logging
logger = logging.getLogger('order_execution')

class OrderExecution(ABC):
    """
    Abstract base class defining the interface for order execution.
    """
    @abstractmethod
    def execute_order(self, order: Dict) -> Dict:
        """
        Execute a trading order.
        
        Args:
            order (Dict): Order details including symbol, quantity, price, and side
        
        Returns:
            Dict: Order execution result
        """
        pass

class OrderExecutor(OrderExecution):
    def __init__(self, exchange_client: Optional[RESTClient], trading_pair: str, paper_trading: bool = False):
        """
        Initialize the OrderExecutor with the exchange client and trading pair.

        Args:
            exchange_client: Coinbase API client instance (can be None in paper trading mode)
            trading_pair: Trading pair symbol (e.g., 'BTC-USD')
            paper_trading: Flag to enable paper trading mode
        """
        self.exchange = exchange_client
        self.trading_pair = trading_pair
        self.paper_trading = paper_trading
        self.positions = {}  # Tracks current positions, keys are trading pairs; values are dicts with 'quantity' and 'entry_price'
        self.default_fill_price = Decimal("50000.0")  # Used for market orders in paper trading if no price is provided
        if self.exchange is None and not self.paper_trading:
            raise ValueError("Exchange client cannot be None in live trading mode")
        logger.info(f"OrderExecutor initialized for {trading_pair} in {'PAPER TRADING' if paper_trading else 'LIVE'} mode")

    def execute_order(self, order: Dict) -> Dict:
        """
        Execute a trading order.
        
        Args:
            order (Dict): Order details including symbol, quantity, price, and side
        
        Returns:
            Dict: Order execution result
        """
        # Extract order details
        side = order.get('side', '').lower()
        size = Decimal(str(order.get('quantity', 0)))
        order_type = order.get('type', 'market').lower()
        limit_price = Decimal(str(order.get('price'))) if order.get('price') else None
        try:
            logger.info(f"Executing {side} order: {size} {self.trading_pair}")

            # Basic input validation
            if side not in ['buy', 'sell']:
                raise ValueError(f"Invalid order side: {side}")
            if order_type not in ['market', 'limit']:
                raise ValueError(f"Invalid order type: {order_type}")
            if order_type == 'limit' and limit_price is None:
                raise ValueError("Limit price required for limit orders")

            if self.paper_trading:
                # Simulate order execution in paper trading mode.
                # For market orders, use default_fill_price; for limit orders, use the provided limit_price.
                fill_price = self.default_fill_price if order_type == 'market' else limit_price
                order = {
                    'id': 'paper_trade',
                    'product_id': self.trading_pair,
                    'side': side,
                    'type': order_type,
                    'size': str(size),
                    'price': str(fill_price),
                    'status': 'filled'
                }
                logger.info(f"Paper trade executed successfully: {order['id']}")
                self._update_position(side, size, fill_price)
                return order

            # For live trading, ensure exchange client is available
            if self.exchange is None:
                raise ValueError("Exchange client not initialized")

            # Prepare order parameters
            order_params = {
                'product_id': self.trading_pair,
                'side': side,
                'type': order_type,
                'size': str(size)
            }
            if order_type == 'limit':
                order_params['price'] = str(limit_price)

            # Execute order through the exchange
            response = self.exchange.place_order(**order_params)
            # Attempt to extract the executed price from the response; fallback to default_fill_price if not present
            executed_price = Decimal(response.get('price', str(self.default_fill_price)))
            logger.info(f"Order executed successfully: {response.get('id', 'unknown')}")
            self._update_position(side, size, executed_price)
            return response

        except Exception as e:
            logger.error(f"Order execution failed: {str(e)}")
            raise

    def create_order(self, symbol: str, side: str, quantity: Decimal, price: Optional[Decimal] = None, order_type: str = 'market') -> Dict:
        """
        A wrapper method to execute_order, providing a more user-friendly interface.

        Args:
            symbol: The trading pair
            side: 'buy' or 'sell'
            quantity: The quantity to buy or sell
            price: Optional limit price
            order_type: Order type, defaults to market

        Returns:
            Dict containing order details
        """
        return self.execute_order(side, quantity, order_type, price)

    def get_position(self, symbol: str) -> Optional[Dict]:
        """
        Returns the current position for a symbol or None if no position exists.
        """
        return self.positions.get(symbol)

    def initialize_position(self, symbol: str, quantity: Decimal, entry_price: Decimal):
        """
        Initializes a position for a given symbol.

        Args:
            symbol: The trading pair
            quantity: The initial quantity
            entry_price: The entry price for the position
        """
        self.positions[symbol] = {'quantity': quantity, 'entry_price': entry_price}
        logger.info(f"Initialized position for {symbol}: {quantity} @ {entry_price}")

    def _update_position(self, side: str, size: Decimal, price: Decimal):
        """
        Updates the position tracking based on the trade.

        Args:
            side: 'buy' or 'sell'
            size: The size of the trade
            price: The price at which the trade was executed.
        """
        if side == 'buy':
            # Initialize the position if it doesn't exist
            if self.trading_pair not in self.positions:
                self.positions[self.trading_pair] = {'quantity': size, 'entry_price': price}
            else:
                current_position = self.positions[self.trading_pair]
                new_quantity = current_position['quantity'] + size
                # Calculate the new weighted average entry price
                new_entry_price = ((current_position['quantity'] * current_position['entry_price']) + (size * price)) / new_quantity
                self.positions[self.trading_pair] = {'quantity': new_quantity, 'entry_price': new_entry_price}
        elif side == 'sell':
            if self.trading_pair not in self.positions:
                raise ValueError("No position exists")
            current_position = self.positions[self.trading_pair]
            if size > current_position['quantity']:
                raise ValueError("Insufficient position size")
            new_quantity = current_position['quantity'] - size
            if new_quantity == 0:
                del self.positions[self.trading_pair]
            else:
                self.positions[self.trading_pair]['quantity'] = new_quantity
