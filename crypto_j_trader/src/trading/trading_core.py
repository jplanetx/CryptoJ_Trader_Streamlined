"""
Core trading functionality implementation
"""
from datetime import datetime
from typing import Dict, Any, Optional
import asyncio
import logging
from decimal import Decimal
import json

logger = logging.getLogger(__name__)

# Add module-level attribute for patching
MarketDataHandler = None  # Allows tests to patch TradingCore.MarketDataHandler

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
            class DummyOrderExecutor:
                async def create_order(self, symbol, side, size, price):
                    return {'id': 'dummy_order'}
                async def get_position(self, symbol):
                    return {'quantity': 0, 'entry_price': 0}
            self.order_executor = DummyOrderExecutor()
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
        # Use provided trading pair or default from config or fallback to "BTC-USD"
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

    def get_position(self, symbol: str) -> Dict[str, float]:
        """Get current position for a symbol."""
        if symbol not in self.positions:
            self.positions[symbol] = {
                'size': 0.0,
                'entry_price': 0.0,
                'unrealized_pnl': 0.0,
                'stop_loss': 0.0
            }
        return self.positions[symbol].copy()

    async def execute_order(self, side: str, size: float, price: float, symbol: str) -> dict:
        if size <= 0 or price <= 0:
            return {'status': 'error', 'message': 'Invalid size or price'}
        
        position = self.get_position(symbol)
        # Always use paper trading mode by instantiating the simplified OrderExecutor
        from .order_execution import OrderExecutor
        self.order_executor = OrderExecutor(trading_pair=symbol)

        try:
            order = await self.order_executor.create_order(
                symbol, side, Decimal(str(size)), Decimal(str(price))
            )
            # Simplified position update:
            if side.lower() == 'buy':
                position['size'] += size
                position['entry_price'] = price
            else:
                position['size'] -= size
            self.positions[symbol] = position
            return {'status': 'success', 'order_id': order.get('order_id')}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    async def check_positions(self):
        """Check all positions for stop loss/take profit triggers."""
        # Iterate over a copy of the symbols to avoid runtime error
        for symbol in list(self.positions.keys()):
            position = self.positions[symbol]
            current_price = self.market_prices.get(symbol)
            if not current_price:
                continue

            if position['stop_loss'] > 0:
                if (position['size'] > 0 and current_price <= position['stop_loss']) or \
                   (position['size'] < 0 and current_price >= position['stop_loss']):
                    await self.execute_order(
                        'sell' if position['size'] > 0 else 'buy',
                        abs(position['size']),
                        current_price,
                        symbol
                    )

    async def update_market_price(self, symbol: str, price: float):
        """Update current market price and check stops."""
        self.market_prices[symbol] = price
        position = self.positions.get(symbol, {})
        
        # Update unrealized PnL
        if position.get('size', 0) != 0:
            position['unrealized_pnl'] = (
                (price - position['entry_price']) * position['size']
                if position['size'] > 0
                else (position['entry_price'] - price) * abs(position['size'])
            )

        if self.market_data_handler:
            await self.market_data_handler.update_price(symbol)

        await self.check_positions()

    async def emergency_shutdown(self):
        logger.warning("Initiating emergency shutdown")
        # Close all positions
        for symbol in list(self.positions.keys()):
            if self.positions[symbol]['size'] != 0:
                current_price = self.market_prices.get(symbol, self.positions[symbol]['entry_price'])
                await self.execute_order(
                    'sell' if self.positions[symbol]['size'] > 0 else 'buy',
                    abs(self.positions[symbol]['size']),
                    current_price,
                    symbol
                )
                del self.positions[symbol]
        self.shutdown_requested = True
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