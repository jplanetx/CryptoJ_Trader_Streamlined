"""
Order Execution Module
Implements the OrderExecutor class responsible for executing trading orders.
"""

import logging
from decimal import Decimal
from typing import Dict, Optional
from coinbase.rest import RESTClient

# Configure logging
logger = logging.getLogger('order_execution')

class OrderExecutor:
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
        if self.exchange is None and not self.paper_trading:
            raise ValueError("Exchange client cannot be None in live trading mode")
        logger.info(f"OrderExecutor initialized for {trading_pair} in {'PAPER TRADING' if paper_trading else 'LIVE'} mode")

    def execute_order(self, side: str, size: Decimal, order_type: str = 'market', limit_price: Decimal = None) -> Dict:
        """
        Execute a trading order with basic error handling.
        
        Args:
            side: 'buy' or 'sell'
            size: Order size
            order_type: 'market' or 'limit'
            limit_price: Required for limit orders
            
        Returns:
            Dict containing order details
        """
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
                # Simulate order execution in paper trading mode
                order = {
                    'id': 'paper_trade',
                    'product_id': self.trading_pair,
                    'side': side,
                    'type': order_type,
                    'size': str(size),
                    'price': str(limit_price) if limit_price else 'market',
                    'status': 'filled'
                }
                logger.info(f"Paper trade executed successfully: {order['id']}")
                return order
            
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
            
            # Execute order through exchange
            response = self.exchange.place_order(**order_params)
            order = response if hasattr(response, 'id') else response
            
            logger.info(f"Order executed successfully: {order.get('id', 'unknown')}")
            return order
            
        except Exception as e:
            logger.error(f"Order execution failed: {str(e)}")
            raise
