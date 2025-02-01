"""Position and risk management system."""
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import numpy as np
from decimal import Decimal

logger = logging.getLogger(__name__)

class PositionManager:
    def __init__(self, config: Dict[str, Any]):
        """Initialize position manager."""
        self.config = config
        self.positions = {}
        self.volatility_windows = {}  # Store price history for volatility calculation
        self.position_limits = config.get('position_limits', {
            'max_position_value': 10000.0,  # Maximum position value in quote currency
            'max_leverage': 3.0,  # Maximum leverage
            'min_position_size': 0.001  # Minimum position size
        })

    def calculate_position_size(self, trading_pair: str, account_value: float, 
                              current_price: float, volatility: float) -> float:
        """
        Calculate optimal position size based on account value and market conditions.
        
        Args:
            trading_pair: Trading pair symbol
            account_value: Total account value in quote currency
            current_price: Current market price
            volatility: Current market volatility
            
        Returns:
            float: Recommended position size
        """
        try:
            # Get risk parameters from config
            risk_per_trade = self.config.get('risk_per_trade', 0.02)  # 2% risk per trade
            max_position_value = self.position_limits['max_position_value']
            
            # Calculate base position size from account value
            base_position_value = account_value * risk_per_trade
            
            # Adjust based on volatility
            volatility_multiplier = 1.0 / (1.0 + volatility)  # Reduce size as volatility increases
            adjusted_value = base_position_value * volatility_multiplier
            
            # Ensure within limits
            position_value = min(adjusted_value, max_position_value)
            
            # Convert to base currency units
            position_size = position_value / current_price
            
            # Round to appropriate precision
            precision = self.config.get('size_precision', {}).get(trading_pair, 8)
            position_size = round(position_size, precision)
            
            # Ensure above minimum size
            if position_size < self.position_limits['min_position_size']:
                position_size = 0.0  # Don't trade if too small
                
            return position_size
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return 0.0

    def calculate_volatility(self, trading_pair: str, price_history: list, 
                           window_size: int = 20) -> float:
        """
        Calculate market volatility using standard deviation of returns.
        
        Args:
            trading_pair: Trading pair symbol
            price_history: List of historical prices
            window_size: Number of periods for volatility calculation
            
        Returns:
            float: Calculated volatility
        """
        try:
            if len(price_history) < window_size:
                return 0.0
                
            # Calculate returns
            prices = np.array(price_history[-window_size:])
            returns = np.log(prices[1:] / prices[:-1])
            
            # Calculate annualized volatility
            daily_vol = np.std(returns)
            annualized_vol = daily_vol * np.sqrt(365)
            
            return float(annualized_vol)
            
        except Exception as e:
            logger.error(f"Error calculating volatility: {e}")
            return 0.0

    def update_volatility_window(self, trading_pair: str, price: float):
        """Update price history for volatility calculation."""
        if trading_pair not in self.volatility_windows:
            self.volatility_windows[trading_pair] = []
            
        self.volatility_windows[trading_pair].append(price)
        
        # Keep limited history
        max_window = 100
        if len(self.volatility_windows[trading_pair]) > max_window:
            self.volatility_windows[trading_pair] = self.volatility_windows[trading_pair][-max_window:]

    def calculate_dynamic_take_profit(self, trading_pair: str, entry_price: float, 
                                    position_size: float, volatility: float) -> Dict[str, Any]:
        """
        Calculate dynamic take-profit levels based on market conditions.
        
        Args:
            trading_pair: Trading pair symbol
            entry_price: Position entry price
            position_size: Current position size
            volatility: Current market volatility
            
        Returns:
            Dict with take-profit levels and sizes
        """
        try:
            # Base take-profit levels
            base_levels = [
                {'pct': 0.02, 'size': 0.3},  # Take 30% at 2% profit
                {'pct': 0.05, 'size': 0.5},  # Take 50% at 5% profit
                {'pct': 0.10, 'size': 1.0}   # Take remaining at 10% profit
            ]
            
            # Adjust based on volatility
            volatility_multiplier = 1.0 + volatility
            adjusted_levels = []
            
            for level in base_levels:
                adjusted_level = {
                    'pct': level['pct'] * volatility_multiplier,
                    'size': level['size'],
                    'price': entry_price * (1.0 + level['pct'] * volatility_multiplier),
                    'quantity': position_size * level['size']
                }
                adjusted_levels.append(adjusted_level)
                
            return {
                'levels': adjusted_levels,
                'volatility_multiplier': volatility_multiplier
            }
            
        except Exception as e:
            logger.error(f"Error calculating take-profit levels: {e}")
            return {'levels': base_levels, 'volatility_multiplier': 1.0}

    def validate_position_risk(self, trading_pair: str, new_position_size: float, 
                             current_price: float, account_value: float) -> Dict[str, Any]:
        """
        Validate if new position meets risk management criteria.
        
        Args:
            trading_pair: Trading pair symbol
            new_position_size: Proposed new position size
            current_price: Current market price
            account_value: Total account value
            
        Returns:
            Dict with validation result and details
        """
        try:
            position_value = abs(new_position_size * current_price)
            current_leverage = position_value / account_value
            
            # Check against limits
            max_position_value = self.position_limits['max_position_value']
            max_leverage = self.position_limits['max_leverage']
            
            validation = {
                'valid': True,
                'messages': [],
                'metrics': {
                    'position_value': position_value,
                    'leverage': current_leverage,
                    'value_limit_pct': position_value / max_position_value * 100,
                    'leverage_limit_pct': current_leverage / max_leverage * 100
                }
            }
            
            if position_value > max_position_value:
                validation['valid'] = False
                validation['messages'].append(
                    f"Position value {position_value} exceeds limit {max_position_value}")
            
            if current_leverage > max_leverage:
                validation['valid'] = False
                validation['messages'].append(
                    f"Leverage {current_leverage} exceeds limit {max_leverage}")
            
            return validation
            
        except Exception as e:
            logger.error(f"Error validating position risk: {e}")
            return {
                'valid': False,
                'messages': [str(e)],
                'metrics': {}
            }
