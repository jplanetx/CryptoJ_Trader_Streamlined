"""Market data management and processing."""
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta, timezone
import numpy as np

logger = logging.getLogger(__name__)

class MarketDataManager:
    """Manages market data retrieval and processing."""
    
    VALID_GRANULARITIES = [60, 300, 900, 3600, 21600, 86400]  # 1min, 5min, 15min, 1h, 6h, 24h
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize market data manager."""
        self.config = config
        self.api_client = None
        self.last_update: Dict[str, datetime] = {}
        self.cached_data: Dict[str, List[Dict[str, Any]]] = {}
    
    async def get_market_data(self, trading_pair: str) -> List[Dict[str, Any]]:
        """Get historical market data for a trading pair."""
        try:
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
            total_volume = sum(candle['volume'] for candle in data)
            
            # Filter out invalid data points but keep volumes
            valid_data = [
                candle for candle in data 
                if all(candle.get(k) is not None for k in ['open', 'high', 'low', 'close'])
            ]
            
            if not valid_data:
                return {
                    'vwap': 0.0,
                    'volume': total_volume,
                    'high': 0.0,
                    'low': 0.0,
                    'close': 0.0
                }
            
            # Calculate VWAP using valid data points
            vwap = sum(candle['close'] * candle['volume'] for candle in valid_data) / \
                   sum(candle['volume'] for candle in valid_data)
                   
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
    
    async def calculate_indicators(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate technical indicators."""
        try:
            if not data:
                return {
                    'rsi': 0.0,
                    'macd': (0.0, 0.0, 0.0),
                    'bb_upper': 0.0,
                    'bb_lower': 0.0
                }
            
            closes = np.array([candle['close'] for candle in data])
            
            # Calculate RSI
            delta = np.diff(closes)
            gains = np.where(delta > 0, delta, 0)
            losses = np.where(delta < 0, -delta, 0)
            
            avg_gain = np.mean(gains[-14:]) if len(gains) >= 14 else np.mean(gains)
            avg_loss = np.mean(losses[-14:]) if len(losses) >= 14 else np.mean(losses)
            
            rs = avg_gain / avg_loss if avg_loss != 0 else 0
            rsi = 100 - (100 / (1 + rs))
            
            # Calculate MACD
            ema12 = np.mean(closes[-12:]) if len(closes) >= 12 else np.mean(closes)
            ema26 = np.mean(closes[-26:]) if len(closes) >= 26 else np.mean(closes)
            macd_line = ema12 - ema26
            signal_line = np.mean(closes[-9:]) if len(closes) >= 9 else np.mean(closes)
            histogram = macd_line - signal_line
            
            # Calculate Bollinger Bands
            sma20 = np.mean(closes[-20:]) if len(closes) >= 20 else np.mean(closes)
            std20 = np.std(closes[-20:]) if len(closes) >= 20 else np.std(closes)
            
            return {
                'rsi': float(rsi),
                'macd': (float(macd_line), float(signal_line), float(histogram)),
                'bb_upper': float(sma20 + (2 * std20)),
                'bb_lower': float(sma20 - (2 * std20))
            }
            
        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")
            raise
    
    async def check_market_status(self, trading_pair: str) -> Dict[str, str]:
        """Check the current market status."""
        try:
            status = await self.api_client.get_market_status(trading_pair)
            return status
        except Exception as e:
            logger.error(f"Error checking market status: {e}")
            return {'status': 'error', 'message': str(e)}
    
    async def verify_data_freshness(self, trading_pair: str) -> bool:
        """Verify if market data is fresh enough."""
        try:
            # Get current ticker to check timestamp
            ticker = await self.get_ticker(trading_pair)
            ticker_time = datetime.fromisoformat(ticker['time'].replace('Z', '+00:00'))
            current_time = datetime.now(timezone.utc)
            
            # Check if ticker is recent (within last minute)
            if current_time - ticker_time > timedelta(minutes=1):
                logger.warning(f"Ticker data is stale for {trading_pair}")
                return False
                
            # Check if we have recent candle data
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