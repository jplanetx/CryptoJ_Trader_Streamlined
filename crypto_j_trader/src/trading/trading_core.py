"""Core trading logic and strategy implementation."""
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from decimal import Decimal

logger = logging.getLogger(__name__)

class TradingBot:
    def __init__(self, config: Dict[str, Any]):
        """Initialize trading bot."""
        self.config = config
        self.positions: Dict[str, Dict] = {}
        self.market_prices: Dict[str, float] = {}
        self.daily_loss = 0.0
        self.is_healthy = True
        self.last_health_check = datetime.now(timezone.utc)
        self.api_client = None
        self.shutdown_requested = False

    async def execute_order(self, side: str, size: float, price: float, trading_pair: str) -> Dict[str, Any]:
        """Execute a trade order."""
        try:
            # Check daily loss limit
            if self.daily_loss >= self.config['risk_management']['max_daily_loss']:
                return {
                    'status': 'error',
                    'error': "Daily loss limit reached"
                }

            # Check position size limits
            position_size = size
            current_position = await self.get_position(trading_pair)
            if side == 'buy':
                total_size = current_position['size'] + position_size
            else:
                total_size = current_position['size'] - position_size

            if abs(total_size) > self.config['risk_management']['max_position_size']:
                return {
                    'status': 'error',
                    'error': f"Position size {abs(total_size)} exceeds limit"
                }

            # Paper trading mode
            if self.config.get('paper_trading', True):
                response = {
                    'status': 'success',
                    'order_id': 'paper_trade',
                    'filled_qty': size,
                    'fill_price': price
                }
            else:
                # Live trading mode
                if not self.api_client:
                    raise ValueError("API client not initialized for live trading")
                response = await self.api_client.place_order(
                    side=side,
                    size=size,
                    price=price,
                    product_id=trading_pair
                )

            # Update position on successful order
            if response['status'] == 'success':
                stop_loss_pct = self.config['risk_management']['stop_loss_pct']
                position_size = size if side == 'buy' else -size
                
                if trading_pair not in self.positions:
                    # New position
                    self.positions[trading_pair] = {
                        'size': position_size,
                        'entry_price': price,
                        'stop_loss': price * (1 - stop_loss_pct if side == 'buy' else 1 + stop_loss_pct),
                        'unrealized_pnl': 0.0
                    }
                else:
                    # Update existing position
                    current_pos = self.positions[trading_pair]
                    new_size = current_pos['size'] + position_size
                    
                    if abs(new_size) < 0.000001:  # Position closed
                        del self.positions[trading_pair]
                    else:
                        # Update average entry price
                        old_value = abs(current_pos['size']) * current_pos['entry_price']
                        new_value = abs(position_size) * price
                        total_size = abs(new_size)
                        avg_price = (old_value + new_value) / total_size
                        
                        self.positions[trading_pair] = {
                            'size': new_size,
                            'entry_price': avg_price,
                            'stop_loss': avg_price * (1 - stop_loss_pct if new_size > 0 else 1 + stop_loss_pct),
                            'unrealized_pnl': current_pos['unrealized_pnl']
                        }

                # Update PnL if we have market price
                if trading_pair in self.market_prices:
                    await self.update_market_price(trading_pair, self.market_prices[trading_pair])
            
            return response

        except Exception as e:
            logger.error(f"Error executing order: {e}")
            return {'status': 'error', 'error': str(e)}

    async def get_position(self, trading_pair: str) -> Dict[str, float]:
        """Get current position details."""
        if trading_pair not in self.positions:
            return {
                'size': 0.0,
                'entry_price': 0.0,
                'unrealized_pnl': 0.0,
                'stop_loss': 0.0
            }
        return self.positions[trading_pair].copy()

    async def update_market_price(self, trading_pair: str, price: float):
        """Update current market price and check positions."""
        self.market_prices[trading_pair] = price
        if trading_pair in self.positions:
            pos = self.positions[trading_pair]
            pos['unrealized_pnl'] = (price - pos['entry_price']) * pos['size']
            
            # Check stop loss
            if (pos['size'] > 0 and price <= pos['stop_loss']) or \
               (pos['size'] < 0 and price >= pos['stop_loss']):
                await self.close_position(trading_pair, price)

    async def close_position(self, trading_pair: str, price: float):
        """Close position at specified price."""
        if trading_pair in self.positions:
            pos = self.positions[trading_pair]
            side = 'sell' if pos['size'] > 0 else 'buy'
            await self.execute_order(side, abs(pos['size']), price, trading_pair)

    async def check_positions(self):
        """Check all positions for stop loss triggers."""
        for pair in list(self.positions.keys()):
            if pair in self.market_prices:
                await self.update_market_price(pair, self.market_prices[pair])

    async def check_health(self) -> bool:
        """Check system health status."""
        try:
            if self.api_client:
                await self.api_client.get_server_time()
            self.last_health_check = datetime.now(timezone.utc)
            return self.is_healthy
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            self.is_healthy = False
            return False

    async def emergency_shutdown(self):
        """Handle emergency shutdown."""
        logger.warning("Emergency shutdown initiated")
        self.is_healthy = False
        self.shutdown_requested = True
        
        # Close all positions at market
        for pair in list(self.positions.keys()):
            pos = self.positions[pair]
            if pos['size'] != 0:
                current_price = self.market_prices.get(pair, pos['entry_price'])
                await self.close_position(pair, current_price)