from typing import Optional, Dict, Any
from decimal import Decimal

class RiskManager:
    def __init__(self, market_data_service, risk_threshold: float, min_position_value: float):
        self.market_data_service = market_data_service
        self.risk_threshold = Decimal(str(risk_threshold))
        self.min_position_value = Decimal(str(min_position_value))
        self.tolerance = Decimal('0.001')  # 0.1% tolerance
        self.loss_limit = self.risk_threshold  # Loss limit equals risk threshold
        self._initialize_thresholds()

    def _initialize_thresholds(self):
        """Initialize risk thresholds with correct multipliers"""
        self.max_position_value = self.risk_threshold * Decimal('2')  # Exactly 2x risk_threshold

    def validate_order(self, order: Dict[str, Any]) -> tuple[bool, str]:
        """
        Validate order with strict priority order:
        1. Required fields
        2. Numeric validation
        3. Side validation
        4. Position checks
        5. Market data checks
        """
        # 1. Required fields validation
        required_fields = {'price', 'size', 'side'}
        missing_fields = required_fields - set(order.keys())
        if missing_fields:
            return False, "Invalid order parameters"

        # 2. Numeric validation
        try:
            price = Decimal(str(order['price']))
            size = Decimal(str(order['size']))
        except (ValueError, TypeError, KeyError):
            return False, "Price and size must be positive"

        if price <= 0 or size <= 0:
            return False, "Price and size must be positive"

        # 3. Side validation
        if order['side'] not in {'buy', 'sell'}:
            return False, "Invalid order parameters"

        # 4. Position and loss limit checks
        position_value = price * size
        max_with_tolerance = self.max_position_value * (1 + self.tolerance)
        loss_with_tolerance = self.loss_limit * (1 + self.tolerance)

        if position_value < self.min_position_value:
            return False, "Order value below minimum position value"
        
        if position_value > max_with_tolerance:
            return False, "Order exceeds maximum position value"

        # Loss limit check
        potential_loss = position_value * Decimal('0.1')  # Assume 10% potential loss
        if potential_loss > loss_with_tolerance:
            return False, "Order exceeds loss limit"

        # 5. Market data and liquidity checks
        recent_prices = self._get_market_data()
        
        if recent_prices:
            # Only apply liquidity checks if we have market data
            avg_price = Decimal(str(sum(recent_prices) / len(recent_prices)))
            price_deviation = abs(price - avg_price) / avg_price
            
            if price_deviation > Decimal('0.1'):  # 10% price deviation threshold
                return False, "Insufficient liquidity"
        else:
            # Allow trading with no market data for small positions
            if position_value > self.risk_threshold:
                return False, "Insufficient market data for large position"

        return True, ""

    def assess_risk(self, price: float, size: float) -> bool:
        """
        Assess risk with safe defaults and proper threshold handling
        """
        try:
            price_dec = Decimal(str(price))
            size_dec = Decimal(str(size))
        except (ValueError, TypeError):
            return False

        if price_dec <= 0 or size_dec <= 0:
            return False

        position_value = price_dec * size_dec
        
        # Skip minimum position check in assess_risk
        # This allows for partial fills and split orders
        
        # Position value check with tolerance
        max_with_tolerance = self.max_position_value * (1 + self.tolerance)
        if position_value > max_with_tolerance:
            return False

        # Market data checks with safe defaults
        recent_prices = self._get_market_data()
        
        # Allow trading with no market data for small positions
        if not recent_prices:
            return position_value <= self.risk_threshold

        # Convert prices to Decimal for consistent calculations
        prices = [Decimal(str(p)) for p in recent_prices]
        
        # Only apply volatility checks for larger positions
        if position_value > self.risk_threshold:
            sorted_prices = sorted(prices)
            if sorted_prices:  # Check if prices list is not empty
                volatility = (sorted_prices[-1] - sorted_prices[0]) / sorted_prices[0]
                if volatility > Decimal('0.05'):  # 5% volatility threshold
                    return False

        return True

    def _get_market_data(self) -> list[float]:
        """
        Safely get market data with error handling
        """
        try:
            prices = self.market_data_service.get_recent_prices()
            return prices if prices else []
        except Exception:
            return []  # Safe default on failure

    def update_risk_threshold(self, new_threshold: float):
        """
        Update risk threshold and recalculate dependent values
        """
        self.risk_threshold = Decimal(str(new_threshold))
        self.loss_limit = self.risk_threshold  # Update loss limit as well
        self._initialize_thresholds()