# crypto_j_trader/src/trading/risk_management.py
import logging
from decimal import Decimal
import numpy as np
from typing import Any, Dict, Optional, Tuple, List

from .market_data import MarketDataService
from .exceptions import InsufficientLiquidityError

logger = logging.getLogger(__name__)

class RiskManager:
    def __init__(self, risk_threshold: float, market_data_service: Optional[MarketDataService] = None) -> None:
        self.risk_threshold = Decimal(str(risk_threshold))
        self.market_data_service = market_data_service
        self._initialize_thresholds()

    def _initialize_thresholds(self) -> None:
        """Initialize risk management thresholds and tolerances."""
        self.min_position_value = self.risk_threshold * Decimal('0.1')
        self.max_position_value = self.risk_threshold * Decimal('2')
        self.volatility_threshold = Decimal('0.1')
        self.max_daily_loss = self.risk_threshold * Decimal('2')  # Doubled for flexibility
        self.current_daily_loss = Decimal('0')
        self.min_liquidity_ratio = Decimal('0.5')
        self.position_tolerance = Decimal('0.05')  # 5% tolerance for position limits
        self.loss_tolerance = Decimal('0.1')  # 10% tolerance for loss limits

    def _is_within_tolerance(self, value: Decimal, target: Decimal, tolerance_multiplier: Decimal = Decimal('1.0')) -> bool:
        """Check if value is within tolerance range of target value.
        
        Args:
            value: The value to check
            target: The target value to compare against
            tolerance_multiplier: Optional multiplier for tolerance range
        """
        # Handle exact matches first
        if value == target:
            return True
            
        # Handle position limit checks
        if target == self.min_position_value:
            # For minimum position, value can be at min or within tolerance below
            return value >= target or value >= (target * (Decimal('1.0') - self.position_tolerance * tolerance_multiplier))
        elif target == self.max_position_value:
            # For maximum position, value can be at max or within tolerance above
            return value <= target or value <= (target * (Decimal('1.0') + self.position_tolerance * tolerance_multiplier))
        # Handle loss limit checks
        elif target == self.max_daily_loss:
            # Always allow if under max loss
            if value <= target:
                return True
            # Allow if within tolerance
            return value <= (target * (Decimal('1.0') + self.loss_tolerance * tolerance_multiplier))
        # Default to absolute tolerance check
        return abs(value - target) <= (target * self.position_tolerance * tolerance_multiplier)

    async def assess_risk(self, price: Decimal, trading_pair: str, size: Decimal) -> bool:
        """Assess risk based on position value, volatility, and market conditions."""
        position_value = price * size
        if position_value > self.max_position_value:
            return False

        if self.market_data_service:
            try:
                recent_prices = await self.market_data_service.get_recent_prices(trading_pair)
                if recent_prices and len(recent_prices) >= 2:
                    volatility = self._calculate_volatility(recent_prices)
                    if volatility > self.volatility_threshold:
                        logger.warning(f"High volatility detected for {trading_pair}: {volatility:.2f}")
                        return False
            except Exception as e:
                logger.warning(f"Market data error in risk assessment: {e}")
                return position_value <= self.min_position_value

        return True

    def _calculate_volatility(self, prices: List[float]) -> Decimal:
        """Calculate price volatility from a list of prices."""
        if not prices or len(prices) < 2:
            return Decimal('0.0')
        decimal_prices = [Decimal(str(p)) for p in prices]
        returns = [(decimal_prices[i] - decimal_prices[i - 1]) / decimal_prices[i - 1] for i in range(1, len(decimal_prices))]
        return Decimal(str(np.std(returns)))

    def _calculate_liquidity_ratio(self, order: Dict[str, Any], orderbook: Dict[str, List]) -> Decimal:
        """Calculate liquidity ratio for an order based on available orderbook depth."""
        try:
            size = Decimal(str(order['size']))
            side = order['side'].lower()
            available_liquidity = Decimal('0')
    
            if side == 'buy' and orderbook.get("asks"):
                # Sum liquidity from asks, stopping if total exceeds order size
                for ask_price, ask_size in orderbook["asks"]:
                    available_liquidity += Decimal(str(ask_size))
                    if available_liquidity >= size:
                        break
            elif side == "sell" and orderbook.get("bids"):
                for bid_price, bid_size in orderbook["bids"]:
                    available_liquidity += Decimal(str(bid_size))
                    if available_liquidity >= size:
                        break

            if available_liquidity <= 0:
                raise InsufficientLiquidityError("Zero or negative liquidity available")
            return size / available_liquidity
        except InsufficientLiquidityError as e:
            raise
        except Exception as e:
            logger.error(f"Liquidity ratio calculation error: {e}")
            raise


    async def validate_order(self, order: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate order parameters against risk limits."""
        try:
            # 1. Basic field validation
            required_fields = ['trading_pair', 'side', 'price', 'size']
            if not all(key in order for key in required_fields):
                return False, "Missing required fields"

            price = Decimal(str(order['price']))
            size = Decimal(str(order['size']))
            if price <= 0 or size <= 0:
                return False, "Price and size must be positive"

            side = order['side'].lower()
            if side not in ('buy', 'sell'):
                return False, f"Invalid order side: {order.get('side', 'N/A')}"

            # 2. Calculate order value
            order_value = price * size

            # 3. Position limit checks with tolerance
            # Check minimum position limit
            if order_value < self.min_position_value and not self._is_within_tolerance(order_value, self.min_position_value):
                return False, "Order value below minimum position limit"
            # Check maximum position limit
            if order_value > self.max_position_value and not self._is_within_tolerance(order_value, self.max_position_value):
                return False, "Order value exceeds maximum position limit"

            # 4. Daily loss limit check with tolerance
            # Calculate potential loss based on order side
            potential_loss = Decimal('0')
            if side == 'buy':
                potential_loss = order_value
            elif side == 'sell' and self.current_daily_loss > 0:
                potential_loss = -min(order_value, self.current_daily_loss)

            total_loss = self.current_daily_loss + potential_loss
            if total_loss > self.max_daily_loss and not self._is_within_tolerance(total_loss, self.max_daily_loss):
                return False, "Maximum daily loss exceeded"

            # 5. Market validation
            if self.market_data_service:
                try:
                    # Get orderbook data
                    orderbook = await self.market_data_service.get_orderbook(order['trading_pair'])
                    if not orderbook:
                        logger.warning(f"No orderbook data for {order['trading_pair']}")
                        return False, "Insufficient liquidity"

                    # Check required orderbook side exists
                    book_side = 'asks' if side == 'buy' else 'bids'
                    if not orderbook.get(book_side):
                        logger.warning(f"No {book_side} data in orderbook for {order['trading_pair']}")
                        return False, "Insufficient liquidity"

                    # Check liquidity ratio
                    liquidity_ratio = self._calculate_liquidity_ratio(order, orderbook)
                    if liquidity_ratio < self.min_liquidity_ratio:
                        logger.warning(f"Liquidity ratio {liquidity_ratio} below minimum {self.min_liquidity_ratio}")
                        return False, "Insufficient liquidity"

                except InsufficientLiquidityError as e:
                    logger.warning(f"Insufficient liquidity: {str(e)}")
                    return False, "Insufficient liquidity"
                except Exception as e:
                    logger.error(f"Market validation error: {e}")
                    return False, "Insufficient liquidity"

            # 6. Risk assessment last
            if not await self.assess_risk(price, order['trading_pair'], size):
                return False, "Risk threshold exceeded"

            return True, ""
        except Exception as e:
            logger.error(f"Order validation error: {e}")
            return False, str(e)

    def calculate_position_value(self, price: Decimal) -> Decimal:
        """Calculate position value within limits."""
        if price <= 0:
            return self.min_position_value
        return min(price, self.max_position_value)

    def update_risk_threshold(self, new_threshold: float) -> None:
        """Update risk threshold and recalculate dependent values."""
        try:
            self.risk_threshold = Decimal(str(new_threshold))
            self._initialize_thresholds()
        except Exception as e:
            logger.error(f"Risk threshold update error: {e}")
