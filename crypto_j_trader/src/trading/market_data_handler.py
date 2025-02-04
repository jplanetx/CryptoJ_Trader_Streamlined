"""
Market data handler interface and adapter classes
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

class MarketDataHandler(ABC):
    """Abstract base class for market data handling"""
    
    @abstractmethod
    def get_last_price(self, trading_pair: str) -> Optional[float]:
        """Get the last known price for a trading pair"""
        pass
    
    @abstractmethod
    async def start(self) -> None:
        """Start the market data handler"""
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """Stop the market data handler"""
        pass

class MarketDataServiceAdapter(MarketDataHandler):
    """Adapter to make MarketDataService compatible with MarketDataHandler interface"""
    
    def __init__(self, market_data_service):
        self.service = market_data_service
    
    def get_last_price(self, trading_pair: str) -> Optional[float]:
        """Get the last known price from the service"""
        return self.service.current_prices.get(trading_pair)
    
    async def start(self) -> None:
        """Start the market data service"""
        # Initialize with some default values
        await self.service.initialize_price_history(["BTC-USD", "ETH-USD"], 1, None)
    
    async def stop(self) -> None:
        """Stop the market data service"""
        await self.service.stop()