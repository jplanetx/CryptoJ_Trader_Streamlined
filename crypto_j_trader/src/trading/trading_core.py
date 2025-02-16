"""
Core trading functionality implementation
"""
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Union
import logging
from decimal import Decimal
import json

logger = logging.getLogger(__name__)

# Add module-level attribute for patching
MarketDataHandler = None  # Allows tests to patch TradingCore.MarketDataHandler

def validate_trading_pair(trading_pair: str) -> bool:
    """Validate trading pair format (e.g., 'BTC-USD')."""
    import re
    pattern = re.compile(r'^[A-Z]{3,5}-[A-Z]{3,5}$')
    return bool(pattern.match(trading_pair))

"""Core trading bot implementation with consistent configuration and execution"""
from decimal import Decimal
from typing import Dict, Optional, Any
from datetime import datetime
import logging

from .config_manager import ConfigManager
from .paper_trading import PaperTradingExecutor
from .order_executor import OrderExecutor, OrderResponse

logger = logging.getLogger(__name__)

class TradingBot:
    """Core trading bot implementation"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config_manager = ConfigManager()
        self.config = config or self.config_manager.get_test_config()
        
        # Initialize with first trading pair by default
        trading_pairs = self.config.get('trading_pairs', ['BTC-USD'])
        self.trading_pair = trading_pairs[0] if isinstance(trading_pairs, list) else 'BTC-USD'
        
        # Set up executor based on config
        paper_trading_config = self.config.get('paper_trading', {})
        if isinstance(paper_trading_config, dict):
            use_paper_trading = paper_trading_config.get('enabled', True)
        else:
            use_paper_trading = bool(paper_trading_config)
            
        if use_paper_trading:
            self.order_executor = PaperTradingExecutor(trading_pair=self.trading_pair)
        else:
            self.order_executor = OrderExecutor(trading_pair=self.trading_pair)
            
        # Load risk parameters with safe type conversion
        risk_config = self.config.get('risk_management', {})
        if not isinstance(risk_config, dict):
            risk_config = {}
            
        self.max_position_size = Decimal(str(risk_config.get('max_position_size', 5.0)))
        self.stop_loss_pct = float(risk_config.get('stop_loss_pct', 0.05))
        self.max_daily_loss = Decimal(str(risk_config.get('max_daily_loss', 500.0)))
        
        # Initialize tracking variables
        self.daily_trades = 0
        self.daily_volume = Decimal('0')
        self.daily_pnl = Decimal('0')
        self.last_reset = datetime.now()

    async def execute_order(self, side: str, size: float, price: float, symbol: Optional[str] = None) -> OrderResponse:
        """Execute a trade order with risk checks"""
        try:
            symbol = symbol or self.trading_pair
            
            # Validate position size
            if side == 'buy':
                current_position = self.order_executor.get_position(symbol)
                new_size = Decimal(str(size)) + Decimal(str(current_position['size']))
                if new_size > self.max_position_size:
                    return {
                        'status': 'error',
                        'message': f'Position size {new_size} would exceed maximum {self.max_position_size}',
                        'order_id': 'ERROR',
                        'symbol': symbol,
                        'side': side,
                        'size': '0',
                        'price': '0',
                        'type': 'market',
                        'timestamp': datetime.now().isoformat()
                    }
            
            # Execute order
            result = await self.order_executor.execute_order(
                side=side,
                size=size,
                price=price,
                symbol=symbol
            )
            
            # Update daily stats if order was successful
            if result['status'] == 'filled':
                self._update_daily_stats(Decimal(str(size)), Decimal(str(price)))
                
            return result
            
        except Exception as e:
            logger.error(f"Order execution error: {str(e)}")
            return {
                'status': 'error',
                'message': str(e),
                'order_id': 'ERROR',
                'symbol': symbol or '',
                'side': side,
                'size': '0',
                'price': '0',
                'type': 'market',
                'timestamp': datetime.now().isoformat()
            }

    def get_position(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Get current position for a symbol"""
        return self.order_executor.get_position(symbol or self.trading_pair)

    def _update_daily_stats(self, size: Decimal, price: Decimal) -> None:
        """Update daily trading statistics"""
        self.daily_trades += 1
        self.daily_volume += size * price

    def reset_daily_stats(self) -> None:
        """Reset daily trading statistics"""
        self.daily_trades = 0
        self.daily_volume = Decimal('0')
        self.daily_pnl = Decimal('0')
        self.last_reset = datetime.now()

    def get_daily_stats(self) -> Dict[str, Any]:
        """Get current daily trading statistics"""
        return {
            'trades': self.daily_trades,
            'volume': str(self.daily_volume),
            'pnl': str(self.daily_pnl),
            'last_reset': self.last_reset.isoformat()
        }
