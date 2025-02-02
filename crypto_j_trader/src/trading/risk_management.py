import logging
from decimal import Decimal
from typing import Dict, Any, Tuple, List, Optional
from datetime import datetime

class RiskManager:
    """
    Risk Management system for crypto trading operations.
    Handles risk assessment, position validation, and order validation.
    """
    
    def __init__(self, risk_threshold: float, market_data=None):
        self.risk_threshold = Decimal(str(risk_threshold))
        self.market_data = market_data
        self.trading_core = None
        self.emergency_mode = False
        self._risk_thresholds = {
            "volatility": Decimal("0.15"),     # 15% volatility threshold
            "exposure": self.risk_threshold / Decimal("100"),  # Convert from percentage
            "liquidity": Decimal("0.10")       # 10% of available liquidity
        }
        self.logger = logging.getLogger(__name__)
        
        if market_data:
            self.market_data = market_data

    async def validate_paper_trading(self) -> Tuple[bool, str]:
        """Validate paper trading system readiness"""
        try:
            if not self.market_data or not hasattr(self.market_data, 'is_running'):
                return False, "Market data service not initialized"

            if not self.market_data.is_running():
                return False, "Market data not running"

            # Check data freshness
            last_update = await self.market_data.get_last_update_time()
            if (datetime.now() - last_update).seconds > 60:  # 60 second staleness threshold
                return False, "Market data is stale"

            # Check order book depth
            order_book = await self.market_data.get_order_book("BTC-USD")
            if len(order_book.get('bids', [])) < 10:  # Minimum depth of 10
                return False, "Insufficient order book depth"

            return True, "Paper trading validation successful"
        except Exception as e:
            self.logger.error(f"Paper trading validation error: {str(e)}")
            return False, f"Validation error: {str(e)}"

    async def assess_risk(self, price: float, trading_pair: str) -> bool:
        """
        Assess trading risk level based on volatility, exposure, and market conditions.
        Returns False if risk thresholds are exceeded.
        """
        try:
            # Get recent trades for volatility calculation
            recent_trades = await self.market_data.get_recent_trades(trading_pair)
            prices = [Decimal(str(trade['price'])) for trade in recent_trades]
            
            # Calculate volatility
            volatility = self._calculate_volatility(prices)
            if volatility > self._risk_thresholds["volatility"]:
                self.logger.warning(f"Volatility {volatility:.2%} exceeds threshold {self._risk_thresholds['volatility']:.2%}")
                return False

            # Calculate exposure
            position = await self.trading_core.get_position(trading_pair)
            total_value = await self.trading_core.get_total_value()
            exposure = (Decimal(str(position.size)) * Decimal(str(price))) / Decimal(str(total_value)) if total_value > 0 else Decimal("0")
            
            self.logger.info(f"Risk assessment passed: exposure {float(exposure):.2%} within threshold {float(self._risk_thresholds['exposure']):.2%}")
            return exposure <= self._risk_thresholds["exposure"]

        except Exception as e:
            self.logger.error(f"Error during risk assessment: {str(e)}")
            raise

    async def validate_order(self, order: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate trading order against risk parameters and market conditions
        """
        try:
            # Basic parameter validation
            if not self._validate_basic_params(order):
                return False, "Invalid order parameters"

            # Check position limits
            if not await self._check_position_limits(order):
                return False, "Position size limit exceeded"

            # Check liquidity
            order_book = await self.market_data.get_order_book(order['symbol'])
            if order['side'] == 'buy':
                available_liquidity = sum(size for price, size in order_book.get('asks', []))
            else:
                available_liquidity = sum(size for price, size in order_book.get('bids', []))

            if Decimal(str(order['size'])) > Decimal(str(available_liquidity)) * self._risk_thresholds["liquidity"]:
                return False, "Order size exceeds safe liquidity threshold"

            # Risk assessment
            if not await self.assess_risk(order['price'], order['symbol']):
                return False, "Risk limits exceeded"

            return True, "Order validated"

        except Exception as e:
            self.logger.error(f"Order validation error: {str(e)}")
            return False, f"Order validation error: {str(e)}"

    def _validate_basic_params(self, order: Dict[str, Any]) -> bool:
        """Validate basic order parameters"""
        required_fields = ['symbol', 'side', 'size', 'price']
        return all(field in order and order[field] is not None for field in required_fields)

    async def _check_position_limits(self, order: Dict[str, Any]) -> bool:
        """Check if order would exceed position limits"""
        position = await self.trading_core.get_position(order['symbol'])
        new_size = position.size + order['size'] if order['side'] == 'buy' else position.size - order['size']
        return abs(new_size) <= self.config.get('max_position_size', 1.0)

    def _calculate_volatility(self, prices: List[Decimal]) -> Decimal:
        """Calculate price volatility using standard deviation of returns"""
        if len(prices) < 2:
            return Decimal("0")

        returns = [(prices[i] - prices[i-1]) / prices[i-1] 
                  for i in range(1, len(prices))]
        
        mean_return = sum(returns) / len(returns)
        squared_diff_sum = sum((r - mean_return) ** 2 for r in returns)
        
        return (squared_diff_sum / (len(returns) - 1)).sqrt()

    async def validate_new_position(self, position_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate new position against risk limits"""
        validation = {
            "valid": True,
            "errors": []
        }
        
        try:
            # Check emergency mode
            if self.emergency_mode:
                validation["valid"] = False
                validation["errors"].append("System in emergency mode")
                return validation
            
            # Check position size
            if abs(Decimal(str(position_data['size']))) > self.config.get('max_position_size', Decimal("1.0")):
                validation["valid"] = False
                validation["errors"].append("Position size exceeds maximum limit")
            
            # Check market data availability
            if not self.market_data:
                validation["valid"] = False
                validation["errors"].append("Market data not available")
                return validation
            
            return validation
            
        except Exception as e:
            validation["valid"] = False
            validation["errors"].append(f"Validation error: {str(e)}")
            return validation
