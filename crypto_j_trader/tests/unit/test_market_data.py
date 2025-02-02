import pytest
import pytest_asyncio
import asyncio

class DummyMarketData:
    """
    Dummy Market Data system to simulate price updates, order book updates,
    trade history tracking, and data validation for testing purposes.
    """
    def __init__(self):
        self.price = None
        self.order_book = {}
        self.trade_history = []

    async def update_price(self, new_price):
        # Simulate a price update.
        await asyncio.sleep(0.05)
        self.price = new_price
        return self.price

    async def update_order_book(self, new_order_book):
        # Simulate updating the order book.
        await asyncio.sleep(0.05)
        self.order_book = new_order_book
        return self.order_book

    async def update_trade_history(self, trade):
        # Simulate recording a new trade.
        await asyncio.sleep(0.05)
        self.trade_history.append(trade)
        return self.trade_history

    async def validate_data(self):
        # Dummy validation: ensure price is a positive number.
        await asyncio.sleep(0.05)
        if self.price is None or self.price < 0:
            raise ValueError("Invalid price data.")
        return True

@pytest_asyncio.fixture
async def market_data_system():
    """Fixture providing a dummy Market Data system for testing."""
    return DummyMarketData()

class TestMarketData:
    @pytest.mark.asyncio
    async def test_price_updates(self, market_data_system):
        # Test that the price update function correctly assigns the new price.
        new_price = 45000.75
        updated_price = await market_data_system.update_price(new_price)
        assert updated_price == new_price, "Price should be updated to the new value."
        assert market_data_system.price == new_price, "Internal price state should reflect the update."

    @pytest.mark.asyncio
    async def test_order_book_updates(self, market_data_system):
        # Test that the order book is updated correctly.
        new_order_book = {
            "bids": [[44900, 1.5], [44850, 2.0]],
            "asks": [[45050, 1.0], [45100, 1.2]]
        }
        updated_order_book = await market_data_system.update_order_book(new_order_book)
        assert updated_order_book == new_order_book, "Order book should match the new update."
        assert market_data_system.order_book == new_order_book, "Internal order book state should reflect the update."

    @pytest.mark.asyncio
    async def test_trade_history(self, market_data_system):
        # Test that new trades are added to the trade history.
        trade = {"id": 101, "symbol": "BTC", "price": 45000, "quantity": 0.1}
        history = await market_data_system.update_trade_history(trade)
        assert trade in history, "Trade should be recorded in the trade history."
        # Add another trade to verify multiple entries.
        trade2 = {"id": 102, "symbol": "ETH", "price": 3000, "quantity": 1}
        history = await market_data_system.update_trade_history(trade2)
        assert trade2 in history, "Second trade should be recorded in the trade history."
        assert len(history) == 2, "Trade history should contain two trades."

    @pytest.mark.asyncio
    async def test_data_validation(self, market_data_system):
        # Test data validation: valid price should pass.
        await market_data_system.update_price(50000)
        is_valid = await market_data_system.validate_data()
        assert is_valid is True, "Data validation should pass for valid price data."
        # Set invalid price and verify that validation fails.
        await market_data_system.update_price(-100)
        with pytest.raises(ValueError, match="Invalid price data."):
            await market_data_system.validate_data()
