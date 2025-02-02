from decimal import Decimal
import logging
from typing import Any, Dict, Optional, Tuple
from .market_data import MarketDataService
from .exceptions import InsufficientLiquidityError, ValidationError

class RiskManager:
    """
    RiskManager handles risk assessment and management for trading operations.
    """

    def __init__(self, risk_threshold: float, market_data_service: Optional[MarketDataService] = None) -> None:
        """
        Initialize RiskManager with risk threshold and optional market data service.

        Args:
            risk_threshold (float): Maximum acceptable risk threshold.
            market_data_service (Optional[MarketDataService]): Market data service for risk calculations.
        """
        self.risk_threshold = Decimal(str(risk_threshold))
        self.market_data_service = market_data_service
        self.logger = logging.getLogger(__name__)
        self._initialize_thresholds()

    def _initialize_thresholds(self) -> None:
        """Initialize internal risk thresholds and parameters."""
        self.volatility_threshold = Decimal('0.05')  # 5% volatility threshold
        self.max_position_value = self.risk_threshold * Decimal('2')
        self.min_position_value = self.risk_threshold * Decimal('0.1')
        self.min_liquidity_ratio = Decimal('0.1')  # Minimum liquidity ratio required

    async def assess_risk(self, price: float, trading_pair: str) -> bool:
        """
        Assess trading risk based on price and trading pair.

        Args:
            price (float): Current asset price.
            trading_pair (str): Trading pair being assessed.

        Returns:
            bool: True if risk is acceptable, False otherwise.
        """
        try:
            price_decimal = Decimal(str(price))
            
            # Calculate total exposure
            position_value = self.calculate_position_value(price_decimal)
            current_exposure = position_value / self.max_position_value

            # Check if exposure exceeds threshold
            if current_exposure > self.risk_threshold:
                self.logger.warning(
                    f"Current exposure {float(current_exposure)} exceeds threshold {float(self.risk_threshold)}"
                )
                return False

            # Volatility check
            if self.market_data_service:
                recent_prices = await self.market_data_service.get_recent_prices(trading_pair)
                if recent_prices:
                    max_price = Decimal(str(max(recent_prices)))
                    min_price = Decimal(str(min(recent_prices)))
                    volatility = (max_price - min_price) / min_price
                    
                    if volatility > self.volatility_threshold:
                        self.logger.warning(f"High volatility detected: {float(volatility)}")
                        return False

            return True

        except Exception as e:
            self.logger.error(f"Risk assessment error: {str(e)}")
            return False

    async def validate_order(self, order: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate an order against risk parameters and market conditions.

        Args:
            order (Dict[str, Any]): Order details including price, size, and trading pair

        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)

        Raises:
            ValidationError: If order validation fails
            InsufficientLiquidityError: If market liquidity is insufficient
        """
        try:
            # Extract order details
            price = Decimal(str(order.get('price', 0)))
            size = Decimal(str(order.get('size', 0)))
            trading_pair = order.get('trading_pair', '')

            if not all([price, size, trading_pair]):
                return False, "Invalid order parameters"

            # Check basic order validity
            if price <= 0 or size <= 0:
                return False, "Price and size must be positive"

            # Calculate order value
            order_value = price * size

            # Check against position limits
            if order_value < self.min_position_value:
                return False, f"Order value {float(order_value)} below minimum {float(self.min_position_value)}"
            
            if order_value > self.max_position_value:
                return False, f"Order value {float(order_value)} exceeds maximum {float(self.max_position_value)}"

            # Check market liquidity if market data service is available
            if self.market_data_service:
                orderbook = await self.market_data_service.get_orderbook(trading_pair)
                if orderbook:
                    liquidity_ratio = self._calculate_liquidity_ratio(order, orderbook)
                    if liquidity_ratio < self.min_liquidity_ratio:
                        raise InsufficientLiquidityError(
                            f"Insufficient liquidity: {float(liquidity_ratio)} below minimum {float(self.min_liquidity_ratio)}"
                        )

            # Perform risk assessment
            risk_acceptable = await self.assess_risk(float(price), trading_pair)
            if not risk_acceptable:
                return False, "Risk assessment failed"

            return True, None

        except InsufficientLiquidityError as e:
            self.logger.warning(f"Liquidity validation failed: {str(e)}")
            return False, str(e)
        except Exception as e:
            self.logger.error(f"Order validation error: {str(e)}")
            return False, f"Validation error: {str(e)}"

    def _calculate_liquidity_ratio(self, order: Dict[str, Any], orderbook: Dict[str, Any]) -> Decimal:
        """
        Calculate the liquidity ratio for an order against the current orderbook.

        Args:
            order (Dict[str, Any]): Order details
            orderbook (Dict[str, Any]): Current orderbook state

        Returns:
            Decimal: Calculated liquidity ratio
        """
        try:
            side = order.get('side', '').lower()
            size = Decimal(str(order.get('size', 0)))
            
            # Get relevant side of the orderbook
            book_side = orderbook.get('asks' if side == 'buy' else 'bids', [])
            
            # Calculate total available liquidity
            total_liquidity = sum(Decimal(str(level[1])) for level in book_side)
            
            if total_liquidity == 0:
                return Decimal('0')
                
            return size / total_liquidity

        except Exception as e:
            self.logger.error(f"Liquidity ratio calculation error: {str(e)}")
            return Decimal('0')

    def calculate_position_value(self, price: Decimal) -> Decimal:
        """
        Calculate the position value based on price.

        Args:
            price (Decimal): Current asset price.

        Returns:
            Decimal: Calculated position value.
        """
        try:
            # Enhanced position value calculation with lot size consideration
            standard_lot_size = Decimal('100')
            position_value = price * standard_lot_size
            
            # Apply value limits
            if position_value < self.min_position_value:
                return self.min_position_value
                
            return min(position_value, self.max_position_value)
            
        except Exception as e:
            self.logger.error(f"Position value calculation error: {str(e)}")
            return Decimal('0')

    def update_risk_threshold(self, new_threshold: float) -> None:
        """
        Update the risk threshold.

        Args:
            new_threshold (float): New risk threshold value.
        """
        try:
            self.risk_threshold = Decimal(str(new_threshold))
            self._initialize_thresholds()
            self.logger.info(f"Risk threshold updated to: {float(self.risk_threshold)}")
        except Exception as e:
            self.logger.error(f"Risk threshold update error: {str(e)}")
