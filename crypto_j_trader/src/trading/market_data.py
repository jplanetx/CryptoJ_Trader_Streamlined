"""Market data handling system."""
import logging
import json
from typing import Dict, Any, Optional, Set
from datetime import datetime, timezone
from .websocket_handler import WebSocketHandler

logger = logging.getLogger(__name__)

class MarketDataHandler:
    def __init__(self, config: Dict[str, Any]):
        """Initialize market data handler."""
        self.config = config
        self.is_running = False
        self._ws_handler = WebSocketHandler(config)
        self.subscriptions: Set[str] = set()
        self._last_update = datetime.now(timezone.utc)

        # Data caches
        self.last_prices: Dict[str, float] = {}
        self.order_books: Dict[str, Dict[str, Any]] = {}
        self.trades: Dict[str, list] = {}
        
        # Bind message handler
        self._ws_handler.add_message_handler(self._handle_message)

    async def start(self) -> None:
        """Start market data handler."""
        if not self.is_running:
            self.is_running = True
            await self._ws_handler.start()
            logger.info("Market data handler started")

    async def stop(self) -> None:
        """Stop market data handler."""
        if self.is_running:
            self.is_running = False
            await self._ws_handler.stop()
            logger.info("Market data handler stopped")

    async def subscribe_to_trading_pair(self, trading_pair: str) -> None:
        """Subscribe to a trading pair's market data."""
        if not self.is_running:
            logger.warning("Cannot subscribe: market data handler not running")
            return

        try:
            await self._ws_handler.subscribe(trading_pair)
            self.subscriptions.add(trading_pair)
            logger.info(f"Subscribed to {trading_pair}")
        except Exception as e:
            logger.error(f"Error subscribing to {trading_pair}: {e}")

    def is_data_fresh(self, max_age_seconds: float = 5.0) -> bool:
        """Check if market data is fresh."""
        age = (datetime.now(timezone.utc) - self._last_update).total_seconds()
        return age <= max_age_seconds

    def get_last_price(self, trading_pair: str) -> Optional[float]:
        """Get the last known price for a trading pair."""
        return self.last_prices.get(trading_pair)

    def get_order_book(self, trading_pair: str) -> Optional[Dict[str, Any]]:
        """Get the current order book for a trading pair."""
        return self.order_books.get(trading_pair)

    def get_recent_trades(self, trading_pair: str, limit: int = 100) -> list:
        """Get recent trades for a trading pair."""
        trades = self.trades.get(trading_pair, [])
        return trades[-limit:] if trades else []

    def _handle_message(self, message: Dict[str, Any]) -> None:
        """Handle incoming WebSocket messages."""
        try:
            message_type = message.get('type', '')
            product_id = message.get('product_id')

            if not product_id:
                return

            self._last_update = datetime.now(timezone.utc)

            if message_type == 'ticker':
                # Update last price
                if 'price' in message:
                    price = float(message['price'])
                    self.last_prices[product_id] = price
                    
            elif message_type == 'l2update':
                # Update order book
                if product_id not in self.order_books:
                    self.order_books[product_id] = {'bids': {}, 'asks': {}}
                
                changes = message.get('changes', [])
                order_book = self.order_books[product_id]
                
                for side, price, size in changes:
                    book_side = 'bids' if side == 'buy' else 'asks'
                    if float(size) == 0:
                        order_book[book_side].pop(price, None)
                    else:
                        order_book[book_side][price] = float(size)
                        
            elif message_type == 'match':
                # Update trades
                if product_id not in self.trades:
                    self.trades[product_id] = []
                    
                trade = {
                    'time': message.get('time'),
                    'price': float(message.get('price', 0)),
                    'size': float(message.get('size', 0)),
                    'side': message.get('side')
                }
                
                self.trades[product_id].append(trade)
                # Keep only last 1000 trades
                if len(self.trades[product_id]) > 1000:
                    self.trades[product_id] = self.trades[product_id][-1000:]

        except Exception as e:
            logger.error(f"Error processing market data message: {e}")

    def get_market_snapshot(self, trading_pair: str) -> Dict[str, Any]:
        """Get current market snapshot for a trading pair."""
        return {
            'trading_pair': trading_pair,
            'last_price': self.last_prices.get(trading_pair),
            'last_update': self._last_update.isoformat(),
            'is_fresh': self.is_data_fresh(),
            'order_book_depth': len(self.order_books.get(trading_pair, {}).get('bids', {})),
            'recent_trades_count': len(self.trades.get(trading_pair, [])),
            'subscribed': trading_pair in self.subscriptions
        }
