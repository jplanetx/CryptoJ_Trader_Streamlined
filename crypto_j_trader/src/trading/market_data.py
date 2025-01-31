"""Market data management and processing."""
import logging
from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timedelta, timezone
import numpy as np
import json

logger = logging.getLogger(__name__)

class MarketDataManager:
    """Manages market data retrieval and processing."""
    
    VALID_GRANULARITIES = [60, 300, 900, 3600, 21600, 86400]  # 1min, 5min, 15min, 1h, 6h, 24h
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize market data manager."""
        self.config = config
        self.api_client = None
        self.ws_handler = None
        self.trading_pairs: Set[str] = set()
        self.last_update: Dict[str, datetime] = {}
        self.cached_data: Dict[str, List[Dict[str, Any]]] = {}
        self.latest_tickers: Dict[str, Dict[str, Any]] = {}
        self._initialize_ws_handler()

    def _initialize_ws_handler(self) -> None:
        """Initialize WebSocket handler with proper configuration."""
        if not self.ws_handler and 'websocket' in self.config:
            from .websocket_handler import WebSocketHandler
            self.ws_handler = WebSocketHandler(self.config)
            self.ws_handler.add_callback(self._handle_ws_message)

    async def start(self) -> None:
        """Start market data manager and initialize connections."""
        if self.ws_handler:
            await self.ws_handler.start()
            # Subscribe to initial trading pairs
            for pair in self.trading_pairs:
                await self.subscribe_to_trading_pair(pair)

    async def stop(self) -> None:
        """Stop market data manager and cleanup connections."""
        if self.ws_handler:
            await self.ws_handler.stop()

    async def subscribe_to_trading_pair(self, trading_pair: str) -> bool:
        """Subscribe to market data for a trading pair."""
        if trading_pair not in self.trading_pairs:
            self.trading_pairs.add(trading_pair)
            if self.ws_handler and self.ws_handler.is_connected:
                success = await self.ws_handler.subscribe(trading_pair)
                if success:
                    logger.info(f"Subscribed to {trading_pair}")
                    return True
                logger.error(f"Failed to subscribe to {trading_pair}")
                return False
        return True

    async def _handle_ws_message(self, message: Dict[str, Any]) -> None:
        """Process incoming WebSocket messages."""
        try:
            msg_type = message.get('type')
            if not msg_type:
                return

            if msg_type == 'ticker':
                # Update ticker cache
                product_id = message.get('product_id')
                if product_id:
                    self.latest_tickers[product_id] = {
                        'price': float(message.get('price', 0)),
                        'volume': float(message.get('volume_24h', 0)),
                        'time': message.get('time', datetime.now(timezone.utc).isoformat())
                    }
                    self.last_update[product_id] = datetime.now(timezone.utc)

            elif msg_type == 'match':
                # Process real-time trade
                product_id = message.get('product_id')
                if product_id:
                    # Update cached data with new trade
                    if product_id not in self.cached_data:
                        self.cached_data[product_id] = []
                    # Add trade to cached data
                    self.cached_data[product_id].append({
                        'timestamp': datetime.fromisoformat(message['time'].replace('Z', '+00:00')).timestamp(),
                        'price': float(message['price']),
                        'size': float(message['size'])
                    })
                    # Trim cache to reasonable size
                    if len(self.cached_data[product_id]) > 1000:
                        self.cached_data[product_id] = self.cached_data[product_id][-1000:]

        except Exception as e:
            logger.error(f"Error processing WebSocket message: {e}")

    async def get_market_data(self, trading_pair: str) -> List[Dict[str, Any]]:
        """Get historical market data for a trading pair."""
        try:
            # First check WebSocket cache
            if trading_pair in self.cached_data:
                return self.cached_data[trading_pair]

            granularity = self.config.get('granularity', 60)
            if granularity not in self.VALID_GRANULARITIES:
                raise ValueError(f"Invalid granularity value: {granularity}")
            
            raw_data = await self.api_client.get_historic_rates(
                product_id=trading_pair,
                granularity=granularity
            )
            
            # Convert raw data to structured format
            formatted_data = []
            for candle in raw_data:
                formatted_data.append({
                    'timestamp': candle[0],
                    'open': float(candle[1]),
                    'high': float(candle[2]),
                    'low': float(candle[3]),
                    'close': float(candle[4]),
                    'volume': float(candle[5])
                })
            
            self.last_update[trading_pair] = datetime.now(timezone.utc)
            self.cached_data[trading_pair] = formatted_data
            return formatted_data
            
        except Exception as e:
            logger.error(f"Error getting market data for {trading_pair}: {e}")
            raise
    
    async def get_ticker(self, trading_pair: str) -> Dict[str, Any]:
        """Get current ticker data for a trading pair."""
        try:
            # First check WebSocket cache
            if trading_pair in self.latest_tickers:
                return self.latest_tickers[trading_pair]

            # Fallback to REST API
            ticker = await self.api_client.get_ticker(product_id=trading_pair)
            return {
                'price': float(ticker['price']),
                'volume': float(ticker['volume']),
                'time': ticker['time']
            }
        except Exception as e:
            logger.error(f"Error getting ticker for {trading_pair}: {e}")
            raise
    
    async def aggregate_market_data(self, data: List[Dict[str, Any]]) -> Dict[str, float]:
        """Aggregate market data into summary statistics."""
        try:
            if not data:
                return self._empty_aggregation()

            total_volume = sum(candle.get('volume', 0) for candle in data)
            
            # Filter out invalid data points but keep volumes
            valid_data = [
                candle for candle in data 
                if all(candle.get(k) is not None for k in ['open', 'high', 'low', 'close'])
            ]
            
            if not valid_data:
                return self._empty_aggregation()
            
            # Calculate VWAP using valid data points
            vwap = sum(candle['close'] * candle.get('volume', 0) for candle in valid_data) / \
                   sum(candle.get('volume', 0) for candle in valid_data)
                   
            return {
                'vwap': float(vwap),
                'volume': float(total_volume),
                'high': float(max(candle['high'] for candle in valid_data)),
                'low': float(min(candle['low'] for candle in valid_data)),
                'close': float(valid_data[-1]['close'])
            }
            
        except Exception as e:
            logger.error(f"Error aggregating market data: {e}")
            raise

    def _empty_aggregation(self) -> Dict[str, float]:
        """Return empty aggregation result."""
        return {
            'vwap': 0.0,
            'volume': 0.0,
            'high': 0.0,
            'low': 0.0,
            'close': 0.0
        }
    
    async def calculate_indicators(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate technical indicators."""
        try:
            if not data:
                return self._empty_indicators()
            
            closes = np.array([candle['close'] for candle in data])
            return {
                'rsi': self._calculate_rsi(closes),
                'macd': self._calculate_macd(closes),
                'bb': self._calculate_bollinger_bands(closes)
            }
            
        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")
            raise

    def _empty_indicators(self) -> Dict[str, Any]:
        """Return empty indicators result."""
        return {
            'rsi': 0.0,
            'macd': (0.0, 0.0, 0.0),
            'bb': (0.0, 0.0)
        }

    def _calculate_rsi(self, closes: np.ndarray, period: int = 14) -> float:
        """Calculate Relative Strength Index."""
        if len(closes) < period + 1:
            return 0.0
            
        delta = np.diff(closes)
        gains = np.where(delta > 0, delta, 0)
        losses = np.where(delta < 0, -delta, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        rs = avg_gain / avg_loss if avg_loss != 0 else 0
        return float(100 - (100 / (1 + rs)))

    def _calculate_macd(self, closes: np.ndarray) -> tuple[float, float, float]:
        """Calculate MACD indicator."""
        if len(closes) < 26:
            return (0.0, 0.0, 0.0)
            
        ema12 = np.mean(closes[-12:])
        ema26 = np.mean(closes[-26:])
        macd_line = ema12 - ema26
        signal_line = np.mean(closes[-9:])
        histogram = macd_line - signal_line
        
        return (float(macd_line), float(signal_line), float(histogram))

    def _calculate_bollinger_bands(self, closes: np.ndarray, period: int = 20) -> tuple[float, float]:
        """Calculate Bollinger Bands."""
        if len(closes) < period:
            return (0.0, 0.0)
            
        sma = np.mean(closes[-period:])
        std = np.std(closes[-period:])
        
        return (float(sma + (2 * std)), float(sma - (2 * std)))
    
    async def check_market_status(self, trading_pair: str) -> Dict[str, str]:
        """Check the current market status."""
        try:
            # Check WebSocket connection health
            if self.ws_handler and not self.ws_handler.is_healthy:
                return {
                    'status': 'error',
                    'message': 'WebSocket connection unhealthy'
                }

            # Check API client health
            if self.api_client:
                status = await self.api_client.get_market_status(trading_pair)
                return status
            
            return {
                'status': 'error',
                'message': 'No API client available'
            }

        except Exception as e:
            logger.error(f"Error checking market status: {e}")
            return {'status': 'error', 'message': str(e)}
    
    async def verify_data_freshness(self, trading_pair: str) -> bool:
        """Verify if market data is fresh enough."""
        try:
            current_time = datetime.now(timezone.utc)
            
            # Check WebSocket connection health
            if self.ws_handler and not self.ws_handler.is_healthy:
                logger.warning("WebSocket connection is unhealthy")
                return False

            # Check ticker freshness
            if trading_pair in self.latest_tickers:
                ticker_time = datetime.fromisoformat(
                    self.latest_tickers[trading_pair]['time'].replace('Z', '+00:00')
                )
                if current_time - ticker_time > timedelta(minutes=1):
                    logger.warning(f"Ticker data is stale for {trading_pair}")
                    return False
            
            # Check candle data freshness
            last_update = self.last_update.get(trading_pair)
            if not last_update or current_time - last_update > timedelta(minutes=1):
                logger.warning(f"Candle data is stale for {trading_pair}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error verifying data freshness: {e}")
            return False
    
    def get_cached_data(self, trading_pair: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached market data if available and fresh."""
        last_update = self.last_update.get(trading_pair)
        if not last_update:
            return None
            
        if datetime.now(timezone.utc) - last_update > timedelta(minutes=1):
            return None
            
        return self.cached_data.get(trading_pair)