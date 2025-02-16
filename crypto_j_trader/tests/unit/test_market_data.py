import pytest
import asyncio
import json
from decimal import Decimal
from typing import Dict, List, Any, Optional
from crypto_j_trader.src.trading.market_data import MarketDataService
from crypto_j_trader.tests.utils.fixtures.config_fixtures import mock_exchange_service

@pytest.mark.unit
class TestMarketDataService:  # Renamed test class
    @pytest.mark.asyncio
    async def test_price_history_management(self, mock_exchange_service: Any) -> None: # Using fixture as parameter
        """Test price history storage and retrieval"""
        # Mock exchange service to return historical data
        mock_exchange = mock_exchange_service
        symbols = ["BTC-USD"]
        history_days = 1
        historical_data = {"BTC-USD": [100.0, 101.0, 102.0]}
        mock_exchange.get_historical_data.return_value = historical_data

        # Initialize MarketDataService with the mock exchange service
        market_data_service = MarketDataService() # Removed unnecessary config
        await market_data_service.initialize_price_history(symbols, history_days, mock_exchange) # Passing mock_exchange

        # Assert price history is initialized correctly
        assert "BTC-USD" in market_data_service.price_history
        assert list(market_data_service.price_history["BTC-USD"]) == historical_data["BTC-USD"]

    @pytest.mark.asyncio
    async def test_get_recent_prices_invalid_trading_pair_type(self) -> None:
        """Test get_recent_prices with invalid trading pair type"""
        market_data_service = MarketDataService()
        with pytest.raises(TypeError):
            await market_data_service.get_recent_prices(123)  # type: ignore

    @pytest.mark.asyncio
    async def test_get_recent_prices(self) -> None:
        """Test get_recent_prices method"""
        market_data_service = MarketDataService()
        trading_pair = "BTC-USD"
        # Simulate price history
        market_data_service.price_history[trading_pair] = [101.0, 102.0, 103.0]
        recent_prices = await market_data_service.get_recent_prices(trading_pair)
        assert recent_prices == [101.0, 102.0, 103.0]

    @pytest.mark.asyncio
    async def test_update_price_history_valid_input(self) -> None:
        """Test update_price_history with valid input"""
        market_data_service = MarketDataService()
        trading_pair = "BTC-USD"
        price = Decimal('104.0')
        await market_data_service.update_price_history(trading_pair, float(price))
        assert trading_pair in market_data_service.price_history
        assert market_data_service.price_history[trading_pair][-1] == float(price)

    @pytest.mark.asyncio
    async def test_update_price_history_invalid_trading_pair_type(self) -> None:
        """Test update_price_history with invalid trading_pair type"""
        market_data_service = MarketDataService()
        with pytest.raises(TypeError, match="Trading pair must be a string"):
            await market_data_service.update_price_history(123, 104.0)  # type: ignore

    @pytest.mark.asyncio
    async def test_update_price_history_invalid_price_type(self) -> None:
        """Test update_price_history with invalid price type"""
        market_data_service = MarketDataService()
        with pytest.raises(TypeError, match="Price must be a number"):
            await market_data_service.update_price_history("BTC-USD", "abc")  # type: ignore

    @pytest.mark.asyncio
    async def test_update_price_history_negative_price(self) -> None:
        """Test update_price_history with negative price"""
        market_data_service = MarketDataService()
        with pytest.raises(ValueError, match="Price cannot be negative"):
            await market_data_service.update_price_history("BTC-USD", -104.0)  # Negative price

    @pytest.mark.asyncio
    async def test_real_time_updates(self, mock_exchange_service: Any) -> None:
        """Test real-time data processing"""
        mock_exchange = mock_exchange_service
        symbols = ["BTC-USD"]
        
        # Set up mock responses
        initial_price = 104.0
        updated_price = 105.0
        
        # Configure mock to return current price
        mock_exchange.get_current_price.return_value = {"BTC-USD": updated_price}
        
        # Configure websocket feed
        async def mock_price_feed(symbols: List[str]) -> Any:
            yield json.dumps({
                "type": "ticker",
                "symbol": "BTC-USD",
                "price": str(updated_price)
            })
        
        mock_exchange.start_price_feed = mock_price_feed
        
        # Initialize MarketDataService
        market_data_service = MarketDataService()
        market_data_service.exchange_service = mock_exchange
        market_data_service.current_prices = {"BTC-USD": initial_price}
        
        # Subscribe and process updates
        await market_data_service.subscribe_price_updates(symbols)
        await asyncio.sleep(0.5)  # Allow time for update
        
        # Verify price update
        assert market_data_service.current_prices["BTC-USD"] == updated_price

    @pytest.mark.asyncio
    async def test_real_time_price_updates_from_websocket(self, mocker: Any, mock_exchange_service: Any) -> None:
        """Test real-time price updates from websocket"""
        mock_exchange = mock_exchange_service
        symbols = ["BTC-USD"]
        updated_price = 106.0

        # Create an async generator for websocket messages
        async def mock_websocket_feed(symbols: List[str]) -> Any:
            yield json.dumps({
                "type": "ticker",
                "symbol": "BTC-USD",
                "price": str(updated_price)
            })

        # Set up the mock
        mock_exchange.start_price_feed = mock_websocket_feed

        # Initialize MarketDataService
        market_data_service = MarketDataService()
        market_data_service.exchange_service = mock_exchange
        market_data_service.current_prices = {"BTC-USD": 105.0}

        # Start websocket feed
        await market_data_service.subscribe_price_updates(symbols)
        
        # Process the websocket message
        await asyncio.sleep(0.5)  # Increased sleep time to ensure message processing

        # Verify the price update
        assert market_data_service.current_prices["BTC-USD"] == updated_price

    @pytest.mark.asyncio
    async def test_error_recovery(self, mock_exchange_service: Any) -> None:
        """Test system recovery from data errors"""
        mock_exchange = mock_exchange_service
        symbols = ["BTC-USD"]
        
        # Test API error handling
        mock_exchange.get_current_price.side_effect = Exception("API Error")
        market_data_service = MarketDataService()
        market_data_service.exchange_service = mock_exchange
        await market_data_service.subscribe_price_updates(symbols)
        
        # Service should continue running despite error
        assert market_data_service._running == False
        
    @pytest.mark.asyncio
    async def test_initialize_price_history_error(self, mock_exchange_service: Any) -> None:
        """Test error handling during price history initialization"""
        mock_exchange = mock_exchange_service
        symbols = ["BTC-USD"]
        mock_exchange.get_historical_data.side_effect = Exception("Historical data error")
        
        market_data_service = MarketDataService()
        with pytest.raises(Exception, match="Historical data error"):
            await market_data_service.initialize_price_history(symbols, 1, mock_exchange)
            
    @pytest.mark.asyncio
    async def test_websocket_json_decode_error(self, mock_exchange_service: Any) -> None:
        """Test handling of malformed JSON in websocket messages"""
        mock_exchange = mock_exchange_service
        symbols = ["BTC-USD"]
        
        # Configure websocket feed to return invalid JSON
        async def mock_invalid_json_feed(symbols: List[str]) -> Any:
            yield "invalid json data"
            
        mock_exchange.start_price_feed = mock_invalid_json_feed
        
        market_data_service = MarketDataService()
        market_data_service.exchange_service = mock_exchange
        market_data_service.current_prices = {"BTC-USD": 100.0}
        
        # Start websocket feed
        await market_data_service.subscribe_price_updates(symbols)
        await asyncio.sleep(0.1)
        
        # Price should remain unchanged after error
        assert market_data_service.current_prices["BTC-USD"] == 100.0
        
    @pytest.mark.asyncio
    async def test_websocket_message_processing_error(self, mock_exchange_service: Any) -> None:
        """Test handling of invalid message format in websocket updates"""
        mock_exchange = mock_exchange_service
        symbols = ["BTC-USD"]
        
        # Configure websocket feed with invalid message format
        async def mock_invalid_format_feed(symbols: List[str]) -> Any:
            yield json.dumps({
                "type": "ticker",
                "symbol": "BTC-USD",
                "price": "invalid_price"  # Invalid price format
            })
            
        mock_exchange.start_price_feed = mock_invalid_format_feed
        
        market_data_service = MarketDataService()
        market_data_service.exchange_service = mock_exchange
        market_data_service.current_prices = {"BTC-USD": 100.0}
        
        # Start websocket feed
        await market_data_service.subscribe_price_updates(symbols)
        await asyncio.sleep(0.1)
        
        # Price should remain unchanged after error
        assert market_data_service.current_prices["BTC-USD"] == 100.0
        
    @pytest.mark.asyncio
    async def test_get_recent_prices_with_error(self) -> None:
        """Test error handling in get_recent_prices"""
        market_data_service = MarketDataService()
        with pytest.raises(TypeError):
            await market_data_service.get_recent_prices(None)  # type: ignore
        
    @pytest.mark.asyncio
    async def test_websocket_connection_cleanup(self, mock_exchange_service: Any) -> None:
        """Test websocket connection cleanup on stop"""
        mock_exchange = mock_exchange_service
        symbols = ["BTC-USD"]
        
        market_data_service = MarketDataService()
        market_data_service.exchange_service = mock_exchange
        market_data_service._running = True
        market_data_service._websocket_task = asyncio.create_task(asyncio.sleep(1))
        
        # Stop service and verify cleanup
        await market_data_service.stop()
        assert market_data_service._running == False
        assert market_data_service._websocket_task is None
        
    @pytest.mark.asyncio
    async def test_subscribe_price_updates_without_exchange(self) -> None:
        """Test error handling when exchange service is not initialized"""
        market_data_service = MarketDataService()
        symbols = ["BTC-USD"]
        
        # Attempt to subscribe without setting exchange_service
        await market_data_service.subscribe_price_updates(symbols)
        
        # Verify service is not running
        assert market_data_service._running == False
        assert market_data_service.exchange_service is None
