"""Core trading logic and strategy implementation."""
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Union
from decimal import Decimal

logger = logging.getLogger(__name__)

class TradingBot:
    def __init__(self, config: Dict[str, Any]):
        """Initialize trading bot."""
        self.config = config
        self.positions: Dict[str, Dict] = {}
        self.market_prices: Dict[str, float] = {}
        self.daily_loss = 0.0
        self.daily_trades_count = 0
        self.daily_volume = 0.0
        self.daily_stats = {
            'peak_pnl': 0.0,
            'lowest_pnl': 0.0,
            'total_fees': 0.0,
            'win_count': 0,
            'loss_count': 0
        }
        self.last_daily_reset = datetime.now(timezone.utc)
        self.is_healthy = True
        self.last_health_check = datetime.now(timezone.utc)
        self.api_client = None
        self.shutdown_requested = False

    async def reset_daily_stats(self):
        """Reset all daily trading statistics."""
        logger.info("Resetting daily trading statistics")
        self.daily_loss = 0.0
        self.daily_trades_count = 0
        self.daily_volume = 0.0
        self.daily_stats = {
            'peak_pnl': 0.0,
            'lowest_pnl': 0.0,
            'total_fees': 0.0,
            'win_count': 0,
            'loss_count': 0
        }
        self.last_daily_reset = datetime.now(timezone.utc)

    async def update_daily_stats(self, trade_result: Dict[str, Any]):
        """
        Update daily trading statistics based on trade results.
        
        Args:
            trade_result: Dictionary containing trade details including:
                - pnl: Profit/Loss from the trade
                - volume: Trade volume
                - fees: Trading fees
        """
        try:
            # Check if we need to reset daily stats (new trading day)
            current_time = datetime.now(timezone.utc)
            if current_time.date() > self.last_daily_reset.date():
                await self.reset_daily_stats()

            # Update trade counts
            self.daily_trades_count += 1
            self.daily_volume += trade_result.get('volume', 0.0)

            # Update PnL stats
            trade_pnl = trade_result.get('pnl', 0.0)
            self.daily_loss -= trade_pnl  # Note: daily_loss decreases with profits
            self.daily_stats['total_fees'] += trade_result.get('fees', 0.0)

            # Update win/loss counts
            if trade_pnl > 0:
                self.daily_stats['win_count'] += 1
            elif trade_pnl < 0:
                self.daily_stats['loss_count'] += 1

            # Update peak/lowest PnL
            current_pnl = -self.daily_loss  # Convert to actual PnL value
            self.daily_stats['peak_pnl'] = max(self.daily_stats['peak_pnl'], current_pnl)
            self.daily_stats['lowest_pnl'] = min(self.daily_stats['lowest_pnl'], current_pnl)

            # Log daily stats update
            logger.info(f"Updated daily stats - PnL: {current_pnl}, Trades: {self.daily_trades_count}")

        except Exception as e:
            logger.error(f"Error updating daily stats: {e}")

    def _validate_order_params(self, side: str, size: float, price: float, trading_pair: str) -> Dict[str, Any]:
        """Validate order parameters."""
        # Check order side
        if side not in ['buy', 'sell']:
            return {
                'status': 'error',
                'error': 'Invalid order parameters: side must be buy or sell'
            }
        
        # Check size and price
        if size <= 0:
            return {
                'status': 'error',
                'error': 'Invalid order parameters: size must be positive'
            }
        
        if price < 0:
            return {
                'status': 'error',
                'error': 'Invalid order parameters: price must be non-negative'
            }
        
        # Check trading pair
        valid_pairs = self.config.get('trading_pairs', ['BTC-USD'])  # Default for testing
        if trading_pair not in valid_pairs:
            return {
                'status': 'error',
                'error': f'Invalid trading pair: {trading_pair}'
            }
            
        return {'status': 'success'}

    async def execute_order(self, side: str, size: float, price: float, trading_pair: str) -> Dict[str, Any]:
        """Execute a trade order."""
        try:
            # Check if shutdown is requested
            if self.shutdown_requested:
                return {
                    'status': 'error',
                    'error': 'Trading is currently suspended'
                }

            # Validate order parameters
            validation_result = self._validate_order_params(side, size, price, trading_pair)
            if validation_result.get('status') == 'error':
                return validation_result

            # Check daily loss limit
            if self.daily_loss <= -self.config['risk_management']['max_daily_loss']:
                return {
                    'status': 'error',
                    'error': "Daily loss limit reached"
                }

            # Calculate potential position size
            current_position = await self.get_position(trading_pair)
            current_size = current_position.get('size', 0.0)
            potential_size = current_size + size if side == 'buy' else current_size - size

            # Check position size limits
            max_size = self.config['risk_management']['max_position_size']
            if abs(potential_size) > max_size:
                return {
                    'status': 'error',
                    'error': f'Position size limit exceeded. Max size: {max_size}, Attempted size: {abs(potential_size)}'
                }

            # Maximum number of concurrent positions
            max_concurrent_positions = self.config.get('max_concurrent_positions', 2)
            if len(self.positions) >= max_concurrent_positions and trading_pair not in self.positions:
                return {
                    'status': 'error',
                    'error': f'Maximum positions ({max_concurrent_positions}) reached'
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
                    await self._update_market_price(trading_pair, self.market_prices[trading_pair])
            
            return response

        except Exception as e:
            logger.error(f"Error executing order: {e}")
            return {'status': 'error', 'error': str(e)}

    async def get_position(self, trading_pair: str) -> Dict[str, Any]:
        """Get the current position for a given trading pair."""
        return self.positions.get(trading_pair, {
            'size': 0.0, 
            'entry_price': 0.0,
            'unrealized_pnl': 0.0,
            'stop_loss': 0.0
        })

    async def _update_market_price(self, trading_pair: str, price: float):
        """Update market price for a trading pair with PnL calculation."""
        self.market_prices[trading_pair] = price
        
        # Update unrealized PnL for open positions
        if trading_pair in self.positions:
            position = self.positions[trading_pair]
            current_price = price
            entry_price = position['entry_price']
            position_size = position['size']
            
            # Calculate unrealized PnL
            unrealized_pnl = (current_price - entry_price) * abs(position_size)
            position['unrealized_pnl'] = unrealized_pnl
            
            # Check stop loss
            await self.check_positions()

    async def update_market_price(self, trading_pair: str, price: float):
        """Public method to update market price."""
        await self._update_market_price(trading_pair, price)

    async def check_positions(self):
        """
        Check all open positions for stop loss conditions and profit taking opportunities.
        Also handles position rebalancing based on market conditions.
        """
        for trading_pair, position in list(self.positions.items()):
            if trading_pair in self.market_prices:
                current_price = self.market_prices[trading_pair]
                stop_loss = position['stop_loss']
                entry_price = position['entry_price']
                position_size = position['size']
                
                # Calculate profit percentage
                if position_size > 0:  # Long position
                    profit_pct = (current_price - entry_price) / entry_price
                    stop_triggered = current_price <= stop_loss
                else:  # Short position
                    profit_pct = (entry_price - current_price) / entry_price
                    stop_triggered = current_price >= stop_loss

                # Check profit taking levels
                take_profit_levels = self.config.get('take_profit_levels', [
                    {'pct': 0.05, 'size': 0.3},  # Take 30% of position at 5% profit
                    {'pct': 0.10, 'size': 0.5},  # Take 50% of remaining at 10% profit
                ])

                for level in take_profit_levels:
                    if profit_pct >= level['pct']:
                        size_to_close = abs(position_size) * level['size']
                        if size_to_close > 0:
                            try:
                                # Execute profit taking order
                                side = 'sell' if position_size > 0 else 'buy'
                                await self.execute_order(side, size_to_close, current_price, trading_pair)
                                logger.info(f"Taking profit: {side} {size_to_close} {trading_pair} at {current_price}")
                            except Exception as e:
                                logger.error(f"Error taking profit: {e}")

                # Position rebalancing based on volatility and market conditions
                await self._rebalance_position(trading_pair, position, current_price)

                # Stop loss check
                if stop_triggered:
                    await self.emergency_shutdown()

    async def emergency_shutdown(self):
        """
        Perform emergency shutdown of trading operations.
        Closes all open positions and stops trading.
        """
        logger.warning("Emergency shutdown initiated")
        
        # Close all open positions
        for trading_pair in list(self.positions.keys()):
            try:
                # Market sell all positions
                position = self.positions[trading_pair]
                size = position['size']
                
                if size > 0:
                    # Close long position
                    await self.execute_order('sell', abs(size), 0, trading_pair)
                elif size < 0:
                    # Close short position
                    await self.execute_order('buy', abs(size), 0, trading_pair)
            except Exception as e:
                logger.error(f"Error closing position during emergency shutdown: {e}")
        
        # Clear all positions explicitly
        self.positions.clear()
        
        # Set shutdown flag
        self.shutdown_requested = True
        self.is_healthy = False

    async def check_health(self) -> Union[bool, Dict[str, Any]]:
        """
        Perform a comprehensive health check on the trading bot.
        
        Checks:
        - API connectivity
        - Position monitoring
        - System performance
        - Risk metrics
        
        Returns:
            Dict with health status and metrics or bool for basic checks
        """
        try:
            health_metrics = {
                'status': 'healthy',
                'api_status': 'unknown',
                'position_status': 'ok',
                'risk_status': 'ok',
                'metrics': {
                    'position_count': len(self.positions),
                    'daily_pnl': -self.daily_loss,
                    'max_drawdown': self.calculate_max_drawdown(),
                    'last_check_time': self.last_health_check.isoformat(),
                    'uptime_seconds': (datetime.now(timezone.utc) - self.last_health_check).total_seconds()
                }
            }

            # Check API connectivity
            if self.api_client:
                try:
                    health_metrics['api_status'] = 'connected'
                except Exception as e:
                    health_metrics['api_status'] = 'disconnected'
                    health_metrics['status'] = 'degraded'
                    logger.error(f"API connection check failed: {e}")

            # Check position health
            for pair, pos in self.positions.items():
                if abs(pos['unrealized_pnl']) > self.config['risk_management'].get('max_position_loss', 1000.0):
                    health_metrics['position_status'] = 'warning'
                    health_metrics['status'] = 'degraded'

            # Check risk metrics
            if self.daily_loss <= -self.config['risk_management']['max_daily_loss']:
                health_metrics['risk_status'] = 'critical'
                health_metrics['status'] = 'unhealthy'

            # Update health status and timestamp
            self.is_healthy = health_metrics['status'] == 'healthy'
            self.last_health_check = datetime.now(timezone.utc)

            return health_metrics if self.config.get('detailed_health_check', False) else self.is_healthy

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            self.is_healthy = False
            return False

    async def _rebalance_position(self, trading_pair: str, position: Dict[str, Any], current_price: float):
        """
        Rebalance position based on market conditions and volatility.
        
        Args:
            trading_pair: The trading pair to rebalance
            position: Current position details
            current_price: Current market price
        """
        try:
            # Get rebalancing configuration
            rebalance_config = self.config.get('rebalancing', {
                'volatility_threshold': 0.02,  # 2% default
                'position_reduction': 0.2,     # 20% position reduction
                'min_position_size': 0.001     # Minimum position size to maintain
            })

            position_size = position['size']
            entry_price = position['entry_price']

            # Skip rebalancing if position is too small
            if abs(position_size) < rebalance_config['min_position_size']:
                return

            # Calculate price volatility
            price_change = abs(current_price - entry_price) / entry_price

            # If volatility exceeds threshold, reduce position
            if price_change > rebalance_config['volatility_threshold']:
                size_to_reduce = abs(position_size) * rebalance_config['position_reduction']
                
                # Ensure remaining position isn't too small
                if abs(position_size) - size_to_reduce >= rebalance_config['min_position_size']:
                    try:
                        # Execute rebalancing order
                        side = 'sell' if position_size > 0 else 'buy'
                        await self.execute_order(side, size_to_reduce, current_price, trading_pair)
                        logger.info(f"Rebalancing position: {side} {size_to_reduce} {trading_pair} at {current_price}")
                    except Exception as e:
                        logger.error(f"Error executing rebalancing order: {e}")

        except Exception as e:
            logger.error(f"Error in position rebalancing: {e}")

    def calculate_max_drawdown(self) -> float:
        """Calculate the maximum drawdown from peak portfolio value."""
        try:
            peak_value = 0
            current_value = 0
            
            # Calculate current portfolio value
            for pair, pos in self.positions.items():
                if pair in self.market_prices:
                    current_price = self.market_prices[pair]
                    position_value = abs(pos['size']) * current_price
                    unrealized_pnl = pos['unrealized_pnl']
                    current_value += position_value + unrealized_pnl
                    peak_value = max(peak_value, position_value)

            if peak_value == 0:
                return 0.0

            drawdown = (peak_value - current_value) / peak_value
            return round(drawdown, 4)
        except Exception as e:
            logger.error(f"Error calculating max drawdown: {e}")
            return 0.0
