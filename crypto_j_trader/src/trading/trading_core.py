"""
Core trading functionality implementation
"""
from datetime import datetime
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

class TradingBot:
    def __init__(self,
                 config: Dict[str, Any],
                 trading_pair: Optional[str] = None,
                 order_executor=None,
                 market_data_handler=None,
                 risk_manager=None):
        # Support string config by loading JSON
        if isinstance(config, str):
            with open(config, 'r') as f:
                config = json.load(f)
        self.config = config
        self.order_executor = order_executor
        self.market_data_handler = market_data_handler
        self.risk_manager = risk_manager
        
        # Use proper dummy order executor if none provided
        if self.order_executor is None:
            from .order_execution import OrderExecutor
            self.order_executor = OrderExecutor(trading_pair=trading_pair or "BTC-USD")
        
        if self.market_data_handler is None:
            # Use a dummy MarketDataHandler that implements both update_price and get_current_price.
            class DummyMarketDataHandler:
                async def update_price(self, symbol):
                    pass
                def get_current_price(self, symbol):
                    return 50000.0  # fixed default price
            self.market_data_handler = DummyMarketDataHandler()
        
        self.positions = {}
        self.is_healthy = True
        self.last_health_check = datetime.now()
        self.daily_loss = 0.0
        self.market_prices = {}
        self.shutdown_requested = False
        self.daily_stats = {
            'trades': 0,
            'volume': 0.0,
            'pnl': 0.0
        }
        self._init_from_config()
        # Validate and use provided trading pair or default from config or fallback to "BTC-USD"
        if trading_pair and not validate_trading_pair(trading_pair):
            raise ValueError(f"Invalid trading pair format: {trading_pair}")
        if trading_pair:
            self.trading_pair = trading_pair
        elif self.trading_pairs:
            self.trading_pair = self.trading_pairs[0]
        else:
            self.trading_pair = self.config.get("default_trading_pair", "BTC-USD")
        # Expose market data handler for legacy tests
        self.MarketDataHandler = MarketDataHandler

    def _init_from_config(self):
        """Initialize internal state from config."""
        self.trading_pairs = self.config.get('trading_pairs', [])
        if not self.trading_pairs:
            self.trading_pairs = self.config.get('trading', {}).get('symbols', [])

    async def update_price(self, symbol: str, price: float):
        """Update price for a symbol."""
        if self.market_data_handler:
            await self.market_data_handler.update_price(symbol)
            self.market_prices[symbol] = price

    async def validate_order(self, symbol: str, side: str, size: float, price: float) -> bool:
        """Validate order parameters."""
        if not validate_trading_pair(symbol):
            return False
        if side not in ['buy', 'sell']:
            return False
        if size <= 0 or price <= 0:
            return False
        return True

    async def get_current_price(self, symbol: str) -> float:
        """Get current price for a symbol."""
        if symbol in self.market_prices:
            return self.market_prices[symbol]
        elif self.market_data_handler:
            return self.market_data_handler.get_current_price(symbol)
        return 0.0

    async def get_position(self, symbol: str) -> Dict[str, float]:
        """Get current position for a symbol.""" 
        if symbol not in self.positions:
            return {
                "size": 0.0,
                "entry_price": 0.0,
                "stop_loss": 0.0
            }

        pos = self.positions[symbol]
        # Handle both dict and Decimal position formats
        if isinstance(pos, dict):
            return pos
        else:
            # Convert Decimal to dict format
            return {
                "size": float(pos),
                "entry_price": float(self.market_prices.get(symbol, 0)),
                "stop_loss": float(self.market_prices.get(symbol, 0) * Decimal("0.95"))
            }

    async def execute_order(self, side: str, size: float, price: float, symbol: str) -> dict:
        """Execute a trade order."""
        # Validate parameters
        if size <= 0:
            return {'status': 'error', 'message': 'Invalid size'}
        if price <= 0:
            return {'status': 'error', 'message': 'Invalid price'}

        # Check position limits
        max_size = self.config.get('risk_management', {}).get('max_position_size', float('inf'))
        position = await self.get_position(symbol)  # Fix: Await the coroutine
        new_size = abs(position['size'] + (size if side == 'buy' else -size))
        
        if new_size > max_size:
            return {'status': 'error', 'message': 'position size limit exceeded'}

        # Check daily loss limit
        max_daily_loss = self.config.get('risk_management', {}).get('max_daily_loss', float('inf'))
        if abs(self.daily_loss) > max_daily_loss:
            return {'status': 'error', 'message': 'daily loss limit exceeded'}

        try:
            result = await self.order_executor.execute_order(
                side=side,
                size=size,
                price=price,
                symbol=symbol
            )
            
            if result['status'] == 'filled':
                # Update market price and position
                self.market_prices[symbol] = price
                
                # Update position using dict format
                curr_pos = await self.get_position(symbol)  # Fix: Await the coroutine
                size_dec = Decimal(str(size))
                if side == 'buy':
                    new_size = curr_pos['size'] + float(size_dec)
                else:
                    new_size = curr_pos['size'] - float(size_dec)
                
                self.positions[symbol] = {
                    'size': new_size,
                    'entry_price': price,
                    'stop_loss': price * 0.95 if new_size > 0 else 0.0
                }
                
                # Update daily stats
                self.daily_stats['trades'] += 1
                self.daily_stats['volume'] += size * price

                # Map 'filled' to 'success' for consistency
                result['status'] = 'success'

            return result

        except ValueError as e:
            # Propagate validation errors
            return {'status': 'error', 'message': str(e)}
        except Exception as e:
            logger.error(f"Order execution failed: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    async def check_positions(self):
        """Check all positions for stop loss/take profit triggers."""
        for symbol in list(self.positions.keys()):
            position = await self.get_position(symbol)  # Fix: Await the coroutine
            if position and position['size'] == 0:
                continue
                
            current_price = self.market_prices.get(symbol, position['entry_price'])
            
            # Check stop loss
            if position['size'] > 0 and current_price <= position['stop_loss']:
                await self.execute_order('sell', position['size'], current_price, symbol)
            elif position['size'] < 0 and current_price >= position['stop_loss']:
                await self.execute_order('buy', abs(position['size']), current_price, symbol)

    async def update_market_price(self, symbol: str, price: float):
        """Update current market price and check stops."""
        self.market_prices[symbol] = price
        await self.check_positions()

    async def emergency_shutdown(self):
        """Execute emergency shutdown procedure."""
        logger.warning("Initiating emergency shutdown")
        self.shutdown_requested = True
        
        # Close all positions
        for symbol in list(self.positions.keys()):
            position = await self.get_position(symbol)
            if position and position['size'] != 0:
                await self.execute_order(
                    'sell' if position['size'] > 0 else 'buy',
                    abs(position['size']),
                    self.market_prices.get(symbol, position['entry_price']),
                    symbol
                )
                
        self.is_healthy = False
        return {'status': 'success'}

    async def check_health(self) -> Dict[str, Any]:
        """Check system health status."""
        self.last_health_check = datetime.now()
        
        health_status = {
            'status': 'healthy' if self.is_healthy and not self.shutdown_requested else 'unhealthy',
            'last_check': self.last_health_check.isoformat(),
            'api_status': True,  # Placeholder
            'metrics': {
                'cpu_usage': 0,  # Placeholder
                'memory_usage': 0,  # Placeholder
                'order_latency': 0,  # Placeholder
            }
        }
        return health_status

    def get_daily_stats(self) -> Dict[str, Any]:
        """Get daily trading statistics."""
        return self.daily_stats.copy()

    async def reset_daily_stats(self):
        """Reset daily trading statistics."""
        self.daily_stats = {
            'trades': 0,
            'volume': 0.0,
            'pnl': 0.0
        }
        self.daily_loss = 0.0

    def get_system_status(self) -> Dict[str, Any]:
        """Get complete system status."""
        return {
            'health': self.is_healthy,
            'last_check': self.last_health_check.isoformat(),
            'positions': self.positions.copy(),
            'daily_stats': self.daily_stats.copy(),
            'shutdown_requested': self.shutdown_requested
        }

    async def reset_system(self):
        """Reset system to initial state."""
        await self.emergency_shutdown()
        self.positions = {}       # clear all positions
        self.market_prices = {}   # reset market prices
        await self.reset_daily_stats()
        self.is_healthy = True
        self.shutdown_requested = False

    def get_system_health(self) -> bool:
        # Return overall system health as a boolean
        return self.is_healthy
