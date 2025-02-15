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
    """Core trading bot implementation"""
    
    def __init__(self, config: Dict[str, Any], trading_pair: Optional[str] = None, *args, **kwargs):
        """Initialize trading bot with configuration"""
        # Support string config by loading JSON
        if isinstance(config, str):
            with open(config, 'r') as f:
                config = json.load(f)
        self.config = config
        self.paper_trading = config.get('paper_trading', False)
        self.positions = {}
        self.market_prices = {}
        self.is_healthy = True
        self.shutdown_requested = False
        self.daily_loss = Decimal('0')
        self.daily_volume = Decimal('0')
        self.daily_trades = 0
        
        # Initialize components
        self.trading_pairs = config.get('trading_pairs', [])
        if not self.trading_pairs:
            self.trading_pairs = config.get('trading', {}).get('symbols', ['BTC-USD'])
            
        # Initialize order executor
        self.order_executor = kwargs.get('order_executor')
        if not self.order_executor:
            from crypto_j_trader.src.trading.order_executor import OrderExecutor
            self.order_executor = OrderExecutor(self, trading_pair=trading_pair or self.trading_pairs[0])

        # Initialize market data handler only if not in paper trading mode
        self.market_data_handler = kwargs.get('market_data_handler')
        if not self.market_data_handler and not self.paper_trading:
            from crypto_j_trader.src.trading.market_data_handler import MarketDataHandler
            self.market_data_handler = MarketDataHandler()

        # Initialize risk manager
        self.risk_manager = kwargs.get('risk_manager')
        
        # Initialize health monitor
        self.health_monitor = kwargs.get('health_monitor')
        if not self.health_monitor:
            from crypto_j_trader.src.trading.health_monitor import HealthMonitor
            self.health_monitor = HealthMonitor()

    async def execute_order(self, side: str, size: float, price: float, symbol: str) -> Dict:
        """Execute a trade order"""
        try:
            # Convert to decimals
            size_dec = Decimal(str(size))
            price_dec = Decimal(str(price))
            
            # Basic validation
            if size_dec <= 0:
                return {'status': 'error', 'message': 'Invalid size'}
            if price_dec <= 0:
                return {'status': 'error', 'message': 'Invalid price'}
                
            # Check daily loss limit
            if self.daily_loss <= -self.config['risk_management'].get('max_daily_loss', float('inf')):
                return {'status': 'error', 'message': 'daily loss limit exceeded'}
                
            # Check position size limit
            position = await self.get_position(symbol)
            new_size = position['size'] + size_dec if side.lower() == 'buy' else position['size'] - size_dec
            if abs(new_size) > self.config['risk_management'].get('max_position_size', float('inf')):
                return {'status': 'error', 'message': 'position size limit exceeded'}
                
            # Execute order through executor
            result = await self.order_executor.execute_order(side, size_dec, price_dec, symbol)
            
            # If paper trading, always return successful fill
            if self.paper_trading:
                result = {
                    'status': 'filled',
                    'order_id': f'paper-{len(self.positions)}-{datetime.now().timestamp()}',
                    'symbol': symbol,
                    'side': side,
                    'size': str(size_dec),
                    'price': str(price_dec)
                }
            
            # Update daily stats on success
            if result['status'] == 'filled':
                self.daily_trades += 1
                self.daily_volume += size_dec * price_dec
                
                # Update position tracking
                if symbol not in self.positions:
                    self.positions[symbol] = {
                        'size': Decimal('0'),
                        'entry_price': Decimal('0')
                    }
                
                pos = self.positions[symbol]
                if side.lower() == 'buy':
                    total_value = (pos['size'] * pos['entry_price'] + size_dec * price_dec)
                    pos['size'] += size_dec
                    pos['entry_price'] = total_value / pos['size'] if pos['size'] > 0 else Decimal('0')
                else:
                    pos['size'] -= size_dec
                    if pos['size'] == 0:
                        pos['entry_price'] = Decimal('0')
                
            return result
            
        except Exception as e:
            logger.error(f"Order execution error: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    async def get_position(self, symbol: str) -> Dict:
        """Get current position for a symbol"""
        if self.order_executor:
            return self.order_executor.get_position(symbol)
        return {
            'size': Decimal('0'),
            'entry_price': Decimal('0'),
            'current_price': Decimal('0'),
            'unrealized_pnl': Decimal('0'),
            'stop_loss': Decimal('0')
        }

    async def check_health(self) -> Union[Dict, bool]:
        """Check system health status"""
        if self.config.get('detailed_health_check', False):
            health_status = await self.health_monitor.check_health()
            health_status.update({
                'api_status': True,  # Basic API status
                'metrics': {
                    'cpu_usage': 0,  # Placeholder for actual metrics
                    'memory_usage': 0,
                    'order_latency': 0
                }
            })
            return health_status
        return self.is_healthy

    async def update_market_price(self, symbol: str, price: float) -> None:
        """Update market price for a symbol"""
        self.market_prices[symbol] = Decimal(str(price))
        if self.market_data_handler:
            await self.market_data_handler.update_price(symbol)

    async def reset_system(self) -> None:
        """Reset system state"""
        self.positions.clear()
        self.market_prices.clear()
        self.is_healthy = True
        self.shutdown_requested = False
        await self.reset_daily_stats()

    async def reset_daily_stats(self) -> None:
        """Reset daily statistics"""
        self.daily_loss = Decimal('0')
        self.daily_volume = Decimal('0')
        self.daily_trades = 0

    async def emergency_shutdown(self) -> Dict:
        """Execute emergency shutdown procedure"""
        self.shutdown_requested = True
        self.is_healthy = False
        
        # Close all positions
        for symbol in list(self.positions.keys()):
            position = await self.get_position(symbol)
            if position['size'] != 0:
                # Get latest price or use entry price as fallback
                price = self.market_prices.get(symbol, position['entry_price'])
                side = 'sell' if position['size'] > 0 else 'buy'
                await self.execute_order(side, abs(position['size']), float(price), symbol)
        
        return {'status': 'success', 'message': 'Emergency shutdown completed'}

    def get_system_status(self) -> Dict:
        """Get current system status"""
        return {
            'health': self.is_healthy,
            'last_check': datetime.now(timezone.utc).isoformat(),
            'positions': self.positions,
            'daily_stats': {
                'trades': self.daily_trades,
                'volume': float(self.daily_volume),
                'pnl': float(self.daily_loss)
            },
            'shutdown_requested': self.shutdown_requested
        }

    def get_daily_stats(self) -> Dict:
        """Get daily trading statistics"""
        return {
            'trades': self.daily_trades,
            'volume': float(self.daily_volume),
            'pnl': float(self.daily_loss)
        }
