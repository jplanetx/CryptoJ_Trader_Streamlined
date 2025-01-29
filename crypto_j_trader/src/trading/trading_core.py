"""
Simplified core trading functionality focusing on essential components.
Implements basic order execution, position tracking, and health monitoring.
"""

import logging
from typing import Dict, Optional
from decimal import Decimal
import time
from datetime import datetime
from coinbase.rest import RESTClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_core.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('trading_core')

class TradingCore:
    def __init__(self, exchange_client: RESTClient, trading_pair: str, risk_manager=None):
        """
        Initialize trading core with minimal required components.
        
        Args:
            exchange_client: Coinbase API client instance
            trading_pair: Trading pair symbol (e.g., 'BTC-USD')
            risk_manager: Optional RiskManager instance for risk controls
        """
        self.exchange = exchange_client
        self.trading_pair = trading_pair
        self.position: Dict[str, Decimal] = {
            'size': Decimal('0'),
            'entry_price': Decimal('0'),
            'unrealized_pnl': Decimal('0'),
            'stop_loss': Decimal('0')
        }
        self.last_health_check = datetime.now()
        self.is_healthy = True
        self.risk_manager = risk_manager
        
        logger.info(f"Trading Core initialized for {trading_pair}")

    def execute_order(self, side: str, size: Decimal, portfolio_value: Decimal, 
                     order_type: str = 'market', limit_price: Optional[Decimal] = None) -> Dict:
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
            
            # Validate and apply risk controls
            if not self._validate_risk_controls(side, size, portfolio_value):
                raise ValueError("Order rejected by risk controls")
                
            # Basic input validation
            if side not in ['buy', 'sell']:
                raise ValueError(f"Invalid order side: {side}")
            if order_type not in ['market', 'limit']:
                raise ValueError(f"Invalid order type: {order_type}")
            if order_type == 'limit' and limit_price is None:
                raise ValueError("Limit price required for limit orders")
                
            # Get current market price for risk calculations
            current_price = self._get_current_price()

            # Execute order through exchange
            order_params = {
                'product_id': self.trading_pair,
                'side': side,
                'order_configuration': {
                    order_type: {
                        'base_size': str(size)
                    }
                }
            }
            
            if limit_price:
                order_params['order_configuration']['limit']['limit_price'] = str(limit_price)
            
            response = self.exchange.create_order(**order_params)
            order = response.order if hasattr(response, 'order') else response
            
            # Update position tracking
            executed_price = Decimal(order.get('average_filled_price', '0'))
            if executed_price > 0:
                self._update_position(side, size, executed_price)
            
            logger.info(f"Order executed successfully: {order.get('order_id', 'unknown')}")
            return order
            
        except Exception as e:
            logger.error(f"Order execution failed: {str(e)}")
            raise

    def _update_position(self, side: str, size: Decimal, price: Decimal):
        """Update internal position tracking."""
        try:
            if side == 'buy':
                if self.position['size'] == Decimal('0'):
                    self.position['entry_price'] = price
                else:
                    # Calculate new average entry price
                    total_value = (self.position['size'] * self.position['entry_price']) + (size * price)
                    self.position['size'] += size
                    self.position['entry_price'] = total_value / self.position['size']
            else:  # sell
                self.position['size'] -= size
                if self.position['size'] <= Decimal('0'):
                    self.position['size'] = Decimal('0')
                    self.position['entry_price'] = Decimal('0')
                    
            logger.info(f"Position updated - Size: {self.position['size']}, Entry: {self.position['entry_price']}")
            
        except Exception as e:
            logger.error(f"Position update failed: {str(e)}")
            raise

    def check_health(self) -> bool:
        """
        Perform basic health check of trading system.
        
        Returns:
            bool: True if system is healthy, False otherwise
        """
        try:
            current_time = datetime.now()
            
            # Basic connectivity check
            response = self.exchange.get_product(self.trading_pair)
            if not response or not hasattr(response, 'product'):
                raise Exception("Failed to fetch product information")
            
            # Check if we can fetch account balance
            accounts_response = self.exchange.get_accounts()
            if not accounts_response or not hasattr(accounts_response, 'accounts'):
                raise Exception("Failed to fetch account information")
            
            self.last_health_check = current_time
            self.is_healthy = True
            logger.info("Health check passed")
            
            return True
            
        except Exception as e:
            self.is_healthy = False
            logger.error(f"Health check failed: {str(e)}")
            return False

    def _validate_risk_controls(self, side: str, size: Decimal, portfolio_value: Decimal) -> bool:
        """Validate order against risk controls."""
        if not self.risk_manager:
            return True
            
        # Check daily loss limit
        if not self.risk_manager.check_daily_loss_limit(float(portfolio_value)):
            logger.warning("Order rejected: Daily loss limit exceeded")
            return False
            
        # Get position size limits
        max_position = Decimal(str(self.risk_manager.calculate_position_size(
            float(portfolio_value),
            self._calculate_volatility(),
            None  # Correlation matrix not implemented yet
        )))
        
        if side == 'buy' and (self.position['size'] + size) > max_position:
            logger.warning(f"Order rejected: Position size limit exceeded ({size} > {max_position})")
            return False
            
        return True
        
    def _calculate_volatility(self) -> float:
        """Calculate current market volatility."""
        try:
            # Get recent candles for volatility calculation
            candles = self.exchange.get_product_candles(
                self.trading_pair,
                granularity=300,  # 5-minute candles
                limit=30
            )
            
            if not candles:
                return 0.2  # Default volatility if no data
                
            # Calculate returns
            prices = [float(candle.close) for candle in candles]
            returns = np.diff(np.log(prices))
            return float(np.std(returns) * np.sqrt(252 * 24 * 12))  # Annualized
            
        except Exception as e:
            logger.error(f"Volatility calculation failed: {str(e)}")
            return 0.2  # Default volatility on error
            
    def _get_current_price(self) -> Decimal:
        """Get current market price."""
        try:
            ticker = self.exchange.get_product_ticker(self.trading_pair)
            return Decimal(str(ticker.price))
        except Exception as e:
            logger.error(f"Failed to get current price: {str(e)}")
            raise
            
    def update_position_metrics(self):
        """Update position metrics including unrealized P&L."""
        if self.position['size'] == Decimal('0'):
            return
            
        try:
            current_price = self._get_current_price()
            
            # Update unrealized P&L
            if self.position['entry_price'] > Decimal('0'):
                self.position['unrealized_pnl'] = (
                    (current_price - self.position['entry_price']) * 
                    self.position['size']
                )
                
            # Update stop loss if risk manager exists
            if self.risk_manager:
                self.position['stop_loss'] = Decimal(str(
                    self.risk_manager.calculate_stop_loss(
                        float(self.position['entry_price'])
                    )
                ))
                
        except Exception as e:
            logger.error(f"Failed to update position metrics: {str(e)}")
            
    def get_position(self) -> Dict:
        """Get current position information."""
        self.update_position_metrics()
        return {
            'size': float(self.position['size']),
            'entry_price': float(self.position['entry_price']),
            'unrealized_pnl': float(self.position['unrealized_pnl']),
            'stop_loss': float(self.position['stop_loss']),
            'last_health_check': self.last_health_check.isoformat(),
            'is_healthy': self.is_healthy
        }
