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

"""Paper trading implementation with consistent configuration and position management"""
from decimal import Decimal
from typing import Dict, Optional, Any, Union
from datetime import datetime
import logging

from .config_manager import ConfigManager
from .order_executor import OrderExecutor, Position, OrderResponse

logger = logging.getLogger(__name__)

class PaperTradingExecutor(OrderExecutor):
    """Paper trading implementation of OrderExecutor"""
    
    def __init__(self, trading_pair: str):
        super().__init__(trading_pair=trading_pair, mock_mode=True)
        self.config = ConfigManager()
        test_config = self.config.get_test_config()
        
        # Safely extract paper trading config
        paper_config = test_config.get('paper_trading', {})
        if not isinstance(paper_config, dict):
            paper_config = {}
            
        # Initialize with safe defaults
        self.initial_balance = self._safe_decimal(
            paper_config.get('initial_balance'),
            default=100000.0
        )
        self.simulate_slippage = bool(paper_config.get('simulate_slippage', True))
        self.slippage_pct = self._safe_decimal(
            paper_config.get('slippage_pct'),
            default=0.001
        )
        
        self.balance = self.initial_balance
        self.positions: Dict[str, Position] = {}
        self.order_history: Dict[str, OrderResponse] = {}
        
    def _safe_decimal(self, value: Optional[Union[int, float, str, Decimal]], default: float) -> Decimal:
        """Safely convert a value to Decimal with fallback"""
        try:
            if value is None:
                return Decimal(str(default))
            return Decimal(str(value))
        except (TypeError, ValueError):
            return Decimal(str(default))

    async def execute_order(self, side: str, size: float, price: float, symbol: str) -> OrderResponse:
        """Execute a paper trading order"""
        try:
            # Validate parameters through parent class method
            self._validate_order_input(side, size, price, symbol)
            
            # Convert to Decimal for precise calculations
            size_dec = Decimal(str(size))
            price_dec = Decimal(str(price))
            
            # Apply simulated slippage if enabled
            if self.simulate_slippage:
                if side == 'buy':
                    price_dec *= (1 + self.slippage_pct)
                else:
                    price_dec *= (1 - self.slippage_pct)
                    
            # Calculate order cost
            order_cost = size_dec * price_dec
            
            # Validate balance for buys
            if side == 'buy':
                if order_cost > self.balance:
                    return self._create_error_response("Insufficient balance", symbol=symbol)
                self.balance -= order_cost
            else:
                # For sells, validate position exists and is sufficient
                current_position = self.get_position(symbol)
                if current_position['size'] < size_dec:
                    return self._create_error_response("Insufficient position size", symbol=symbol)
                self.balance += order_cost
                
            # Update position
            try:
                self._update_position(symbol, side, size_dec, price_dec)
            except ValueError as e:
                # Rollback balance changes if position update fails
                if side == 'buy':
                    self.balance += order_cost
                else:
                    self.balance -= order_cost
                return self._create_error_response(str(e), symbol=symbol)
                
            # Generate order ID and create response
            order_id = self._generate_order_id()
            
            response = {
                'status': 'success',
                'order_id': order_id,
                'symbol': symbol,
                'side': side,
                'size': str(size_dec),
                'price': str(price_dec),
                'type': 'market',
                'timestamp': datetime.now().isoformat(),
                'message': None
            }
            
            self.order_history[order_id] = response
            return response
            
        except Exception as e:
            logger.error(f"Paper trading order execution error: {str(e)}")
            return self._create_error_response(str(e), symbol=symbol)

    def get_balance(self) -> Decimal:
        """Get current paper trading balance"""
        return self.balance
        
    def get_total_value(self) -> Decimal:
        """Get total portfolio value including positions"""
        total = self.balance
        for pos in self.positions.values():
            # In real implementation, would use current market price
            total += pos.size * pos.entry_price
        return total
        
    def reset(self) -> None:
        """Reset paper trading state"""
        self.balance = self.initial_balance
        self.positions.clear()
        self.order_history.clear()
        self._order_counter = 1000
