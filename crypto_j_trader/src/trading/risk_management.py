import logging
from decimal import Decimal
import numpy as np
from typing import Any, Dict, Optional, Tuple, List, Union
import asyncio  # Add import for asyncio

from .market_data import MarketDataService
from .exceptions import InsufficientLiquidityError
from crypto_j_trader.config import MAX_LIQUIDITY_CONSUMPTION, POSITION_TOLERANCE, LOSS_TOLERANCE  # Import config values

INSUFFICIENT_LIQUIDITY_ERROR = "Insufficient liquidity"
MISSING_FIELDS_ERROR = "Missing required fields"
PRICE_SIZE_ERROR = "Price and size must be positive"
INVALID_SIDE_ERROR = "Invalid order side"
MIN_POSITION_ERROR = "Order value below minimum position limit"
MAX_POSITION_ERROR = "Order value exceeds maximum position limit"
MAX_DAILY_LOSS_ERROR = "Maximum daily loss exceeded"
RISK_THRESHOLD_ERROR = "Risk threshold exceeded"

logger = logging.getLogger(__name__)

def validate_trading_pair(trading_pair: str) -> bool:
    """Validate trading pair format (e.g., 'BTC-USD')."""
    import re
    pattern = re.compile(r'^[A-Z]{3,5}-[A-Z]{3,5}$')
    return bool(pattern.match(trading_pair))

class RiskManager:
    """Manages trading risk controls and validation"""

    def __init__(self, config: Dict):
        """Initialize RiskManager with configuration."""
        self.config = config
        self.risk_config = config.get('risk_management', {})
        self.market_data_service = None
        self.current_daily_loss = Decimal('0')
        
        # Load risk thresholds
        self.risk_threshold = Decimal(str(self.risk_config.get('risk_threshold', '0.75')))
        self.max_position_value = Decimal(str(self.risk_config.get('max_position_value', '100000.0')))
        self.min_position_value = Decimal(str(self.risk_config.get('min_position_value', '100.0')))
        self.max_daily_loss = Decimal(str(self.risk_config.get('max_daily_loss', '10000.0')))
        self.loss_tolerance = Decimal(str(self.risk_config.get('loss_tolerance', '0.1')))
        self.position_tolerance = Decimal(str(self.risk_config.get('position_tolerance', '0.05')))
        self.volatility_threshold = Decimal(str(self.risk_config.get('volatility_threshold', '0.15')))
        self.liquidity_requirement = Decimal(str(self.risk_config.get('liquidity_requirement', '0.5')))

    def _is_within_tolerance(self, value: Decimal, limit: Decimal, tolerance: Decimal, is_minimum: bool = False) -> bool:
        """Check if a value is within tolerance of a limit."""
        if is_minimum:
            min_allowed = limit * (Decimal('1') - tolerance)
            return value >= min_allowed
        else:
            max_allowed = limit * (Decimal('1') + tolerance)
            return value <= max_allowed

    async def validate_order(self, order: Dict) -> Tuple[bool, str]:
        """Validate order against risk parameters."""
        try:
            # Basic order validation
            if not all(k in order for k in ['trading_pair', 'side', 'price', 'size']):
                return False, "Missing required fields"

            size = Decimal(str(order['size']))
            price = Decimal(str(order['price']))
            
            # Calculate order value
            order_value = size * price
            
            # Check minimum position value
            if not self._is_within_tolerance(order_value, self.min_position_value, self.position_tolerance, is_minimum=True):
                return False, "Order value below minimum position limit"
                
            # Check maximum position value
            if not self._is_within_tolerance(order_value, self.max_position_value, self.position_tolerance):
                return False, "Order value exceeds maximum position limit"
            
            # Check liquidity
            if self.market_data_service:
                order_book = await self.market_data_service.get_order_book(order['trading_pair'])
                if not order_book or not (order_book.get('bids') or order_book.get('asks')):
                    return False, "Insufficient liquidity"
                    
                liquidity_ratio = self._calculate_liquidity_ratio(order, order_book)
                if liquidity_ratio > self.liquidity_requirement:
                    return False, "Insufficient liquidity"
            
            # Check daily loss limit
            potential_loss = self._calculate_potential_loss(order)
            total_loss = self.current_daily_loss + potential_loss
            if not self._is_within_tolerance(abs(total_loss), self.max_daily_loss, self.loss_tolerance):
                return False, "Maximum daily loss exceeded"
            
            # Check volatility
            result = await self.assess_risk(order_value, order['trading_pair'], self.volatility_threshold)
            if not result:
                return False, "Risk assessment failed - high volatility or exposure"
            
            return True, "Order validation successful"
            
        except Exception as e:
            logger.error(f"Order validation error: {str(e)}")
            return False, f"Validation error: {str(e)}"

    async def assess_risk(self, position_value: Decimal, trading_pair: str, volatility_limit: Decimal) -> bool:
        """Assess if position meets risk criteria."""
        try:
            if self.market_data_service is None:
                return True  # Default to permissive if no market data
                
            recent_trades = await self.market_data_service.get_recent_trades(trading_pair)
            if not recent_trades:
                return True  # Default to permissive if no trade data
                
            # Calculate volatility
            prices = [Decimal(str(trade['price'])) for trade in recent_trades]
            volatility = self._calculate_volatility(prices)
            
            # High volatility check
            if volatility > volatility_limit:
                return False
                
            # Exposure check
            if position_value > self.max_position_value:
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Risk assessment error: {str(e)}")
            return True  # Default to permissive on error

    def _calculate_volatility(self, prices: List[Decimal]) -> Decimal:
        """Calculate price volatility using standard deviation."""
        if not prices or len(prices) < 2:
            return Decimal('0')
            
        mean = sum(prices) / len(prices)
        squared_diffs = [(p - mean) ** 2 for p in prices]
        variance = sum(squared_diffs) / (len(prices) - 1)
        return (variance.sqrt() / mean)

    def _calculate_liquidity_ratio(self, order: Dict, orderbook: Dict) -> Decimal:
        """Calculate ratio of order size to available liquidity."""
        side = order['side'].lower()
        size = Decimal(str(order['size']))
        
        if side == 'buy':
            book_side = orderbook.get('asks', [])
        else:
            book_side = orderbook.get('bids', [])
            
        if not book_side:
            return Decimal('1')
            
        available_size = sum(Decimal(str(level[1])) for level in book_side)
        if available_size == 0:
            return Decimal('1')
            
        return size / available_size
        
    def _calculate_potential_loss(self, order: Dict) -> Decimal:
        """Calculate potential loss from order."""
        size = Decimal(str(order['size']))
        price = Decimal(str(order['price']))
        return size * price * Decimal('0.01')  # Assume 1% potential loss
        
    def calculate_position_value(self, price: Decimal) -> Decimal:
        """Calculate valid position value from price."""
        if price <= 0:
            return self.min_position_value
        return min(price, self.max_position_value)
