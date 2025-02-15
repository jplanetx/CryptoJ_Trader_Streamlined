"""
This module implements a basic paper trading module for CryptoJ Trader.
It provides a PaperTrader class to simulate trading without using real money,
while maintaining accurate position tracking and risk management.
"""
import json
import logging
import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Optional, List, Union, Any

# Configure logging
logger = logging.getLogger(__name__)
handler = logging.FileHandler('paper_trading.log')
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

class PaperTraderError(Exception):
    """Custom exception for paper trading errors"""
    pass

class TradeHistoryManager:
    """Manages trade history persistence and recovery"""
    def __init__(self, data_dir: str = "data/trades"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self.current_file = None
        self._init_trade_file()
        logger.info(f"TradeHistoryManager initialized with data directory: {data_dir}")
        
    def _init_trade_file(self) -> None:
        # Use timezone-aware UTC now
        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        self.current_file = os.path.join(self.data_dir, f"trades_{date_str}.json")
        if not os.path.exists(self.current_file):
            self._write_trades([])
            logger.info(f"Created new trade history file: {self.current_file}")
            
    def _write_trades(self, trades: List[Dict]) -> None:
        try:
            with open(self.current_file, 'w') as f:
                json.dump(trades, f, indent=2, default=str)
            logger.debug(f"Successfully wrote {len(trades)} trades to {self.current_file}")
        except Exception as e:
            logger.error(f"Failed to write trades: {str(e)}")
            raise PaperTraderError(f"Trade persistence failed: {str(e)}")
            
    def save_trade(self, trade: Dict) -> None:
        try:
            trades = self.load_trades()
            trades.append(trade)
            self._write_trades(trades)
            logger.info(f"Trade saved successfully: {trade}")
        except Exception as e:
            logger.error(f"Failed to save trade: {str(e)}")
            raise PaperTraderError(f"Failed to save trade: {str(e)}")
            
    def load_trades(self, start_date: Optional[datetime] = None) -> List[Dict]:
        try:
            if not os.path.exists(self.current_file):
                logger.info(f"No trade history file found at {self.current_file}")
                return []
            with open(self.current_file) as f:
                trades = json.load(f)
            if start_date:
                trades = [
                    t for t in trades
                    if datetime.fromisoformat(t['timestamp']) >= start_date
                ]
            logger.debug(f"Loaded {len(trades)} trades from {self.current_file}")
            return trades
        except Exception as e:
            logger.error(f"Failed to load trades: {str(e)}")
            return []

class Position:
    """Represents a trading position with detailed tracking information"""
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.size = Decimal("0")
        self.entry_price = Decimal("0")
        self.current_price = Decimal("0")
        self.unrealized_pnl = Decimal("0")
        self.realized_pnl = Decimal("0")
        self.stop_loss = Decimal("0")
        self.trades = []
        self.last_update_time = datetime.now(timezone.utc)
        logger.info(f"New position created for {symbol}")

    def to_dict(self) -> Dict:
        """Convert position to dictionary format"""
        return {
            'symbol': self.symbol,
            'size': self.size,
            'entry_price': self.entry_price,
            'current_price': self.current_price,
            'unrealized_pnl': self.unrealized_pnl,
            'realized_pnl': self.realized_pnl,
            'stop_loss': self.stop_loss,
            'last_update': self.last_update_time.isoformat()
        }

class PaperTrader:
    """Handles paper trading simulation with position tracking"""
    
    def __init__(self, config: Dict, *args, **kwargs):
        """Initialize paper trader with configuration"""
        self.config = config
        self.positions: Dict[str, Position] = {}
        self.orders = {}
        self.order_counter = 1000
        self.market_data = {}
        self.initial_capital = Decimal(str(self.config.get('initial_capital', '100000')))
        self.current_capital = self.initial_capital
        self.daily_pnl = Decimal('0')
        self.max_position_size = Decimal(str(self.config.get('risk_management', {}).get('max_position_size', '10')))
        self.timeout = self.config.get('timeout', 30)
        
    async def execute_order(self, side: str, size: Union[float, Decimal], price: Union[float, Decimal], symbol: str) -> Dict:
        """Execute a paper trading order"""
        try:
            # Convert inputs to Decimal
            size_dec = Decimal(str(size))
            price_dec = Decimal(str(price))
            
            # Validate order
            if size_dec <= 0:
                raise ValueError("Invalid order size")
            if price_dec <= 0:
                raise ValueError("Invalid order price")
                
            # Get or create position
            if symbol not in self.positions:
                self.positions[symbol] = Position(symbol)
            position = self.positions[symbol]
            
            # Check position limits for buys
            if side.lower() == 'buy':
                new_position_size = position.size + size_dec
                if new_position_size > self.max_position_size:
                    raise ValueError("Position size limit exceeded")
            else:  # Selling
                if size_dec > position.size:
                    raise ValueError("Insufficient position size")
                    
            # Update position
            if side.lower() == 'buy':
                total_value = (position.size * position.entry_price + size_dec * price_dec)
                new_size = position.size + size_dec
                position.size = new_size
                position.entry_price = total_value / new_size if new_size > 0 else Decimal('0')
            else:
                realized_pnl = (price_dec - position.entry_price) * size_dec
                position.realized_pnl += realized_pnl
                position.size -= size_dec
                if position.size == 0:
                    position.entry_price = Decimal('0')
                    position.stop_loss = Decimal('0')
            
            position.current_price = price_dec
            position.unrealized_pnl = (price_dec - position.entry_price) * position.size
            if position.size > 0:
                position.stop_loss = position.entry_price * Decimal('0.95')
            
            # Record trade
            trade = {
                'symbol': symbol,
                'side': side.lower(),
                'size': str(size_dec),
                'price': str(price_dec),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            position.trades.append(trade)
            
            # Generate order ID and record
            self.order_counter += 1
            order_id = f'paper-order-{self.order_counter}'
            order_record = {
                'id': order_id,
                'symbol': symbol,
                'side': side.lower(),
                'size': str(size_dec),
                'price': str(price_dec),
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'status': 'filled'
            }
            self.orders[order_id] = order_record
            
            return order_record
            
        except Exception as e:
            logger.error(f"Paper trading order execution error: {str(e)}")
            return {
                'status': 'error',
                'message': str(e),
                'symbol': symbol
            }
            
    def get_position(self, symbol: str) -> Position:
        """Get current position for a symbol"""
        if symbol not in self.positions:
            self.positions[symbol] = Position(symbol)
        return self.positions[symbol]

    def get_position_info(self, symbol: str) -> Dict:
        """Get position information as a dictionary"""
        position = self.get_position(symbol)
        return position.to_dict()
        
    def get(self, order_id: str, default: Any = None) -> Optional[Dict]:
        """Get order details by ID"""
        return self.orders.get(order_id, default)

    def place_order(self, order: Dict) -> Dict:
        """Place a new order"""
        try:
            symbol = order['symbol']
            side = order['side']
            quantity = Decimal(str(order['quantity']))
            price = Decimal(str(order.get('price', self.market_data.get(symbol, '50000'))))
            
            return self.execute_order(side, quantity, price, symbol)
            
        except Exception as e:
            logger.error(f"Order placement error: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }

    def integrate_risk_controls(self, risk_controls: Dict) -> None:
        """Integrate risk control parameters"""
        if 'max_position_size' in risk_controls:
            self.max_position_size = Decimal(str(risk_controls['max_position_size']))
