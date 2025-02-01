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

class TradingBot:
    def __init__(self, 
                 config: Dict[str, Any], 
                 order_executor=None, 
                 market_data_handler=None, 
                 risk_manager=None):
        """Initialize trading bot with dependencies."""
        self.config = config
        self.order_executor = order_executor
        self.market_data_handler = market_data_handler
        self.risk_manager = risk_manager
        
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

    def _init_from_config(self):
        """Initialize internal state from config."""
        self.trading_pairs = self.config.get('trading_pairs', [])
        if not self.trading_pairs:
            self.trading_pairs = self.config.get('trading', {}).get('symbols', [])

    async def get_position(self, symbol: str) -> Dict[str, float]:
        """Get current position for a symbol."""
        if symbol not in self.positions:
            self.positions[symbol] = {
                'size': 0.0,
                'entry_price': 0.0,
                'unrealized_pnl': 0.0,
                'stop_loss': 0.0
            }
        return self.positions[symbol].copy()

    async def execute_order(self, 
                          side: str, 
                          size: float, 
                          price: float, 
                          symbol: str) -> Dict[str, Any]:
        """Execute a trade order."""
        # Validate parameters
        if size <= 0:
            return {'status': 'error', 'message': 'Invalid size'}
        
        if price <= 0:
            return {'status': 'error', 'message': 'Invalid price'}
            
        # Check position limits
        max_size = self.config.get('risk_management', {}).get('max_position_size', float('inf'))
        position = await self.get_position(symbol)
        new_size = abs(position['size'] + (size if side == 'buy' else -size))
        
        if new_size > max_size:
            return {
                'status': 'error', 
                'message': 'position size limit exceeded'
            }
            
        # Check daily loss limit
        max_daily_loss = self.config.get('risk_management', {}).get('max_daily_loss', float('inf'))
        if abs(self.daily_loss) > max_daily_loss:
            return {
                'status': 'error', 
                'message': 'daily loss limit exceeded'
            }
        
        if self.order_executor is None:
            # Paper trading, execute order locally
            order_id = f"paper_{datetime.now().timestamp()}"
            # Update position (simplified for paper trading)
            if side == 'buy':
              position['size'] += size
              if position['size'] > 0 and position['entry_price'] == 0:
                  position['entry_price'] = price # set initial entry price
              elif position['size'] > 0:
                  total_cost = position['size'] * position['entry_price']
                  new_cost = size * price
                  total_size = position['size'] + size
                  position['entry_price'] = (total_cost + new_cost) / total_size if total_size > 0 else 0 # weighted average
            elif side == 'sell':
                if position['size'] > 0:
                    if size > position['size']:
                      return {'status': 'error', 'message': 'Insufficient position size'}
                    position['size'] -= size
                    if position['size'] == 0:
                        del self.positions[symbol]
                elif position['size'] <= 0:
                    position['size'] -= size # selling short
                    if position['size'] < 0:
                      total_cost = abs(position['size']) * position['entry_price']
                      new_cost = size * price
                      total_size = abs(position['size'] + size)
                      position['entry_price'] = (total_cost + new_cost) / total_size if total_size > 0 else 0
            stop_loss_pct = self.config.get('risk_management', {}).get('stop_loss_pct', 0.05)
            if position['size'] > 0:
                position['stop_loss'] = position['entry_price'] * (1 - stop_loss_pct)
            elif position['size'] < 0:
                 position['stop_loss'] = position['entry_price'] * (1 + stop_loss_pct)
            else:
              position['stop_loss'] = 0

            # Update daily stats
            self.daily_stats['trades'] += 1
            self.daily_stats['volume'] += size * price
            self.positions[symbol] = position
            return {
              'status': 'success',
              'order_id': order_id
            }
        
        # Execute order using order executor
        try:
            order = await self.order_executor.create_order(symbol, side, Decimal(str(size)), Decimal(str(price)))
            # Update position from order executor if needed
            if side == 'buy':
              current_position = await self.order_executor.get_position(symbol)
              if current_position:
                  position['size'] = float(current_position['quantity'])
                  position['entry_price'] = float(current_position['entry_price'])
              if position['size'] > 0 and position['entry_price'] == 0:
                position['entry_price'] = price # set initial entry price
              elif position['size'] > 0:
                  total_cost = position['size'] * position['entry_price']
                  new_cost = size * price
                  total_size = position['size'] + size
                  position['entry_price'] = (total_cost + new_cost) / total_size if total_size > 0 else 0 # weighted average
            elif side == 'sell':
                current_position = await self.order_executor.get_position(symbol)
                if current_position:
                    if size > position['size']:
                      return {'status': 'error', 'message': 'Insufficient position size'}
                    position['size'] = float(current_position['quantity'])
                    if position['size'] == 0:
                        position['entry_price'] = 0
                elif position['size'] <= 0:
                    position['size'] -= size # selling short
                    if position['size'] < 0:
                      total_cost = abs(position['size']) * position['entry_price']
                      new_cost = size * price
                      total_size = abs(position['size'] + size)
                      position['entry_price'] = (total_cost + new_cost) / total_size if total_size > 0 else 0
            
            stop_loss_pct = self.config.get('risk_management', {}).get('stop_loss_pct', 0.05)
            if position['size'] > 0:
                position['stop_loss'] = position['entry_price'] * (1 - stop_loss_pct)
            elif position['size'] < 0:
                 position['stop_loss'] = position['entry_price'] * (1 + stop_loss_pct)
            else:
              position['stop_loss'] = 0
            # Update daily stats
            self.daily_stats['trades'] += 1
            self.daily_stats['volume'] += size * price
            self.positions[symbol] = position
            return {
                'status': 'success',
                'order_id': order.get('id', 'unknown')
            }
        except Exception as e:
            logger.error(f"Order execution failed: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }

    async def check_positions(self):
        """Check all positions for stop loss/take profit triggers."""
        for symbol, position in self.positions.items():
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

        await self.check_positions()

    async def emergency_shutdown(self):
        """Execute emergency shutdown procedure."""
        logger.warning("Initiating emergency shutdown")
        self.shutdown_requested = True
        
        # Close all positions
        for symbol, position in list(self.positions.items()):
            if position['size'] != 0:
                current_price = self.market_prices.get(symbol, position['entry_price'])
                await self.execute_order(
                    'sell' if position['size'] > 0 else 'buy',
                    abs(position['size']),
                    current_price,
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
        self.positions = {}
        self.market_prices = {}
        await self.reset_daily_stats()
        self.is_healthy = True
        self.shutdown_requested = False