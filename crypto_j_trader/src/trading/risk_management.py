import logging
from typing import Dict, Optional
from datetime import datetime, timedelta
import numpy as np

logger = logging.getLogger(__name__)

class RiskManager:
    """Manages risk controls and position sizing"""
    
    def __init__(self, config: Dict):
        self.config = config['risk_management']
        self.daily_loss_limit = self.config.get('daily_loss_limit', 0.02)  # 2% default
        self.position_size_limit = self.config.get('position_size_limit', 0.1)  # 10% default
        self.stop_loss_pct = self.config.get('stop_loss_pct', 0.05)  # 5% default
        self.correlation_weight = self.config.get('correlation_weight', 0.3)  # 30% weight for correlation
        self.volatility_weight = self.config.get('volatility_weight', 0.4)  # 40% weight for volatility
        self.min_position_size = self.config.get('min_position_size', 0.02)  # 2% minimum position size
        self.daily_loss = 0.0
        self.last_reset = datetime.now()
        
    def reset_daily_loss(self) -> None:
        """Reset daily loss tracking at market open"""
        if datetime.now() - self.last_reset > timedelta(hours=24):
            self.daily_loss = 0.0
            self.last_reset = datetime.now()
            logger.info("Daily loss tracking reset")
            
    def check_daily_loss_limit(self, portfolio_value: float) -> bool:
        """Check if daily loss limit has been exceeded"""
        self.reset_daily_loss()
        if self.daily_loss <= -abs(self.daily_loss_limit * portfolio_value):
            logger.warning(f"Daily loss limit reached: {-self.daily_loss:.2f}")
            return False
        return True
        
    def calculate_position_size(self, portfolio_value: float, volatility: float,
                              correlation_matrix: Optional[np.ndarray] = None) -> float:
        """Calculate position size based on volatility, correlation risk, and overall risk limits
        
        Args:
            portfolio_value: Current portfolio value
            volatility: Current market volatility
            correlation_matrix: Optional correlation matrix of portfolio assets
        Returns:
            float: Recommended position size in base currency
        """
        # Base Kelly position sizing
        win_prob = 0.55  # Default win probability
        win_loss_ratio = 1.5  # Default win/loss ratio
        kelly_fraction = (win_prob - (1 - win_prob)/win_loss_ratio)
        
        # Volatility adjustment
        volatility_score = min(1.0, 0.1/volatility) if volatility > 0 else 1.0
        
        # Correlation risk adjustment
        correlation_score = 1.0
        if correlation_matrix is not None:
            avg_correlation = self.calculate_correlation_risk(correlation_matrix)
            # Reduce position size as correlation increases
            correlation_score = 1.0 - abs(avg_correlation)
        
        # Calculate final position size with weighted factors
        risk_adjusted_size = (
            kelly_fraction *
            (volatility_score * self.volatility_weight +
             correlation_score * self.correlation_weight)
        )
        
        # Apply limits
        position_size = max(
            min(risk_adjusted_size, self.position_size_limit),
            self.min_position_size
        )
        
        return position_size * portfolio_value
        
    def calculate_atr(self, high_prices: np.ndarray, low_prices: np.ndarray, close_prices: np.ndarray, period: int = 14) -> float:
        """Calculate Average True Range for dynamic stop loss"""
        high_low = high_prices - low_prices
        high_close = np.abs(high_prices - np.roll(close_prices, 1))
        low_close = np.abs(low_prices - np.roll(close_prices, 1))
        
        ranges = np.vstack([high_low, high_close, low_close])
        true_range = np.max(ranges, axis=0)
        
        return np.mean(true_range[-period:])
    
    def calculate_correlation_risk(self, returns_matrix: np.ndarray) -> float:
        """Calculate portfolio correlation risk score
        
        Args:
            returns_matrix: Matrix of asset returns (rows=time, cols=assets)
        Returns:
            float: Risk score based on average correlation
        """
        correlation_matrix = np.corrcoef(returns_matrix.T)
        # Average correlation excluding self-correlation
        np.fill_diagonal(correlation_matrix, np.nan)
        avg_correlation = np.nanmean(correlation_matrix)
        return avg_correlation
        
    def calculate_stop_loss(self, entry_price: float,
                          high_prices: Optional[np.ndarray] = None,
                          low_prices: Optional[np.ndarray] = None,
                          close_prices: Optional[np.ndarray] = None) -> float:
        """Calculate dynamic stop loss based on market volatility
        
        Args:
            entry_price: Entry price of the position
            high_prices: Recent high prices for ATR calculation
            low_prices: Recent low prices for ATR calculation
            close_prices: Recent close prices for ATR calculation
        """
        if high_prices is not None and low_prices is not None and close_prices is not None:
            # Calculate ATR-based stop loss
            atr = self.calculate_atr(high_prices, low_prices, close_prices)
            # Use 2x ATR for stop loss distance
            stop_distance = 2 * atr
            return entry_price * (1 - stop_distance)
        else:
            # Fallback to fixed percentage if price data not available
            return entry_price * (1 - self.stop_loss_pct)
        
    def update_daily_loss(self, pnl: float) -> None:
        """Update daily loss tracking"""
        self.daily_loss += pnl
        logger.debug(f"Updated daily loss: {self.daily_loss:.2f}")