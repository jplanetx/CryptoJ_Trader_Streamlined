import pytest
import pytest_asyncio
from crypto_j_trader.src.trading.market_data import MarketData

@pytest_asyncio.fixture
async def market_data():
    """Fixture providing a MarketData instance for testing."""
    return MarketData()

class TestMarketData:
    """Test suite for the MarketData class."""

    @pytest.mark.asyncio
    async def test_initialization(self, market_data):
        """Test that MarketData is properly initialized with empty price history."""
        assert market_data.price_history == {}, "Price history should be empty on initialization"

    @pytest.mark.asyncio
    async def test_get_recent_prices_empty_history(self, market_data):
        """Test getting prices for a trading pair with no history."""
        prices = await market_data.get_recent_prices("BTC-USD")
        assert prices == [], "Should return empty list for trading pair with no history"

    @pytest.mark.asyncio
    async def test_update_price_history_new_pair(self, market_data):
        """Test updating price history for a new trading pair."""
        trading_pair = "ETH-USD"
        price = 2000.0
        
        await market_data.update_price_history(trading_pair, price)
        prices = await market_data.get_recent_prices(trading_pair)
        
        assert len(prices) == 1, "Should have one price in history"
        assert prices[0] == price, "Price should match the updated value"

    @pytest.mark.asyncio
    async def test_update_price_history_existing_pair(self, market_data):
        """Test updating price history for an existing trading pair."""
        trading_pair = "BTC-USD"
        initial_price = 45000.0
        new_price = 46000.0
        
        await market_data.update_price_history(trading_pair, initial_price)
        await market_data.update_price_history(trading_pair, new_price)
        prices = await market_data.get_recent_prices(trading_pair)
        
        assert len(prices) == 2, "Should have two prices in history"
        assert prices == [initial_price, new_price], "Prices should be in order of addition"

    @pytest.mark.asyncio
    async def test_price_history_limit(self, market_data):
        """Test that price history is limited to 100 entries."""
        trading_pair = "BTC-USD"
        
        # Add 110 prices
        for i in range(110):
            await market_data.update_price_history(trading_pair, float(i))
        
        prices = await market_data.get_recent_prices(trading_pair)
        
        assert len(prices) == 100, "Should maintain only last 100 prices"
        assert prices[0] == 10.0, "Should have removed oldest prices"
        assert prices[-1] == 109.0, "Should have kept most recent prices"

    @pytest.mark.asyncio
    async def test_multiple_trading_pairs(self, market_data):
        """Test handling multiple trading pairs independently."""
        btc_price = 45000.0
        eth_price = 2000.0
        
        await market_data.update_price_history("BTC-USD", btc_price)
        await market_data.update_price_history("ETH-USD", eth_price)
        
        btc_prices = await market_data.get_recent_prices("BTC-USD")
        eth_prices = await market_data.get_recent_prices("ETH-USD")
        
        assert len(btc_prices) == 1, "Should have one BTC price"
        assert len(eth_prices) == 1, "Should have one ETH price"
        assert btc_prices[0] == btc_price, "BTC price should match"
        assert eth_prices[0] == eth_price, "ETH price should match"

    @pytest.mark.asyncio
    async def test_invalid_price_update(self, market_data):
        """Test error handling for invalid price updates."""
        trading_pair = "BTC-USD"
        
        # Test with invalid price type
        try:
            await market_data.update_price_history(trading_pair, "invalid")
            pytest.fail("Should raise exception for invalid price type")
        except Exception:
            prices = await market_data.get_recent_prices(trading_pair)
            assert prices == [], "Should not have added invalid price to history"

    @pytest.mark.asyncio
    async def test_error_handling_get_prices(self, market_data):
        """Test error handling in get_recent_prices."""
        # Force an error by making price_history None
        market_data.price_history = None
        
        prices = await market_data.get_recent_prices("BTC-USD")
        assert prices == [], "Should return empty list on error"

    @pytest.mark.asyncio
    async def test_invalid_trading_pair_type(self, market_data):
        """Test handling of invalid trading pair types."""
        invalid_pairs = [None, 123, {"pair": "BTC-USD"}]
        
        for invalid_pair in invalid_pairs:
            prices = await market_data.get_recent_prices(invalid_pair)
            assert prices == [], "Should return empty list for invalid trading pair type"

    @pytest.mark.asyncio
    async def test_price_history_persistence(self, market_data):
        """Test that price history persists between updates."""
        trading_pair = "BTC-USD"
        prices = [45000.0, 46000.0, 47000.0]
        
        # Add prices sequentially
        for price in prices:
            await market_data.update_price_history(trading_pair, price)
            current_prices = await market_data.get_recent_prices(trading_pair)
            assert price in current_prices, "Added price should be in history"
        
        final_prices = await market_data.get_recent_prices(trading_pair)
        assert final_prices == prices, "Final price history should match all added prices"
