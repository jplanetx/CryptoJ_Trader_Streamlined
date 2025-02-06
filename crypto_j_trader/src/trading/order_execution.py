"""
Order Execution Module
Implements the OrderExecution base class and OrderExecutor class responsible for executing trading orders.
"""

import logging
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Dict, Optional

from .exchange_service import (
    ExchangeService,
    MarketOrder,
    LimitOrder,
    ExchangeServiceError
)

# Configure logging
logger = logging.getLogger('order_execution')

class OrderExecution(ABC):
    """
    Abstract base class defining the interface for order execution.
    """
    @abstractmethod
    async def execute_order(self, order: Dict) -> Dict:
        """
        Execute a trading order.
        
        Args:
            order (Dict): Order details including symbol, quantity, price, and side
        
        Returns:
            Dict: Order execution result
        """
        pass

class OrderExecutor(OrderExecution):
    def __init__(self, exchange_service: Optional[ExchangeService], trading_pair: Optional[str] = None, paper_trading: bool = False):
        """
        Initialize the OrderExecutor with the exchange service and trading pair.

        Args:
            exchange_service: Exchange service instance (can be None in paper trading mode)
            trading_pair: Trading pair symbol (e.g., 'BTC-USD'), can be None for multi-pair trading
            paper_trading: Flag to enable paper trading mode
        """
        self.exchange = exchange_service
        self.trading_pair = trading_pair
        if not trading_pair:
            raise ValueError("Trading pair must be specified in the constructor")
        self.paper_trading = paper_trading
        self.positions = {}  # Tracks current positions, keys are trading pairs; values are dicts with 'quantity' and 'entry_price'
        self.default_fill_price = Decimal("50000.0")  # Used for market orders in paper trading if no price is provided
        if self.exchange is None and not self.paper_trading:
            raise ValueError("Exchange service cannot be None in live trading mode")
        logger.info(f"OrderExecutor initialized in {'PAPER TRADING' if paper_trading else 'LIVE'} mode")

    async def execute_order(self, order: Dict) -> Dict:
        """
        Execute a trading order.
        
        Args:
            order (Dict): Order details including symbol, quantity, price, and side
        
        Returns:
            Dict: Order execution result
        """
        try:
            # Extract order details
            side = order.get('side', '').lower()
            quantity_str = order.get('quantity', '0')
            order_type = order.get('type', 'market').lower()
            price_str = order.get('price')
            
            # Get trading pair from order, fallback to default
            trading_pair = order.get('symbol', self.trading_pair)

            # Basic input validation
            if side not in ['buy', 'sell']:
                raise ValueError(f"Invalid order side: {side}")
            if order_type not in ['market', 'limit']:
                raise ValueError(f"Invalid order type: {order_type}")
            if order_type == 'limit' and price_str is None:
                raise ValueError("Limit price required for limit orders")

            try:
                size = Decimal(str(quantity_str))
            except Exception:
                raise ValueError(f"Invalid literal for Decimal: {quantity_str}")

            limit_price = None
            if price_str:
                try:
                    limit_price = Decimal(str(price_str))
                except:
                    raise ValueError(f"Invalid literal for Decimal: {price_str}")

            logger.info(f"Executing {side} order: {size} {trading_pair}")

            if self.paper_trading:
                # Simulate order execution in paper trading mode
                fill_price = self.default_fill_price if order_type == 'market' else limit_price
                order_result = {
                    'order_id': 'paper_trade',
                    'product_id': trading_pair,
                    'side': side,
                    'type': order_type,
                    'size': str(size),
                    'price': str(fill_price),
                    'status': 'filled'
                }
                logger.info(f"Paper trade executed successfully: {order_result['order_id']}")
                self._update_position(trading_pair, side, size, fill_price)
                return order_result

            # For live trading, ensure exchange service is available
            if self.exchange is None:
                raise ValueError("Exchange service not initialized")

            try:
                # Execute order through the exchange service
                if order_type == 'market':
                    market_order = MarketOrder(
                        product_id=trading_pair,
                        side=side,
                        size=size
                    )
                    response = await self.exchange.place_market_order(market_order)
                else:  # limit order
                    limit_order = LimitOrder(
                        product_id=trading_pair,
                        side=side,
                        size=size,
                        price=limit_price
                    )
                    response = await self.exchange.place_limit_order(limit_order)

                # Get the order details to confirm execution
                order_details = await self.exchange.get_order_status(response['order_id'])
                
                # Extract executed price from order details or use ticker price as fallback
                executed_price = None
                if order_details.get('price'):
                    executed_price = Decimal(str(order_details['price']))
                
                if not executed_price:
                    ticker = await self.exchange.get_product_ticker(trading_pair)
                    if ticker.get('price'):
                        executed_price = Decimal(str(ticker['price']))
                    else:
                        executed_price = self.default_fill_price

                logger.info(f"Order executed successfully: {response.get('order_id', 'unknown')}")
                self._update_position(trading_pair, side, size, executed_price)
                return order_details

            except ExchangeServiceError as e:
                logger.error(f"Exchange service error: {str(e)}")
                raise

        except Exception as e:
            logger.error(f"Order execution failed: {str(e)}")
            raise

    async def create_order(self, symbol: str, side: str, quantity: Decimal, price: Optional[Decimal] = None, order_type: str = 'market') -> Dict:
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
        order = {
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'type': order_type
        }
        if price is not None:
            order['price'] = price
        return await self.execute_order(order)

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

    def _update_position(self, symbol: str, side: str, size: Decimal, price: Decimal):
        """
        Updates the position tracking based on the trade.

        Args:
            symbol: The trading pair symbol
            side: 'buy' or 'sell'
            size: The size of the trade
            price: The price at which the trade was executed
        """
        if side == 'buy':
            # Initialize the position if it doesn't exist
            if symbol not in self.positions:
                self.positions[symbol] = {'quantity': size, 'entry_price': price}
            else:
                current_position = self.positions[symbol]
                new_quantity = current_position['quantity'] + size
                # Calculate the new weighted average entry price
                new_entry_price = ((current_position['quantity'] * current_position['entry_price']) + (size * price)) / new_quantity
                self.positions[symbol] = {'quantity': new_quantity, 'entry_price': new_entry_price}
        elif side == 'sell':
            if symbol not in self.positions:
                raise ValueError(f"No position exists for {symbol}")
            current_position = self.positions[symbol]
            if size > current_position['quantity']:
                raise ValueError(f"Insufficient position size for {symbol}")
            new_quantity = current_position['quantity'] - size
            if new_quantity == 0:
                del self.positions[symbol]
            else:
                self.positions[symbol]['quantity'] = new_quantity
