import pytest
from unittest.mock import AsyncMock, MagicMock
import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from crypto_j_trader.src.trading.market_data import MarketDataHandler


@pytest.fixture
def mock_config():
    return {
      'websocket': {
          'url': 'wss://test.exchange.com',
          'subscriptions': ['BTC-USD'],
        }
    }


@pytest.fixture
def mock_websocket_handler():
    mock = AsyncMock()
    mock.is_connected = True
    return mock

@pytest.fixture
def market_data_handler(mock_config, mock_websocket_handler):
    handler = MarketDataHandler(mock_config)
    handler._ws_handler = mock_websocket_handler
    return handler

@pytest.mark.asyncio
async def test_start_and_stop(market_data_handler, mock_websocket_handler):
    """Test starting and stopping the market data handler"""
    await market_data_handler.start()
    mock_websocket_handler.start.assert_called_once()
    assert market_data_handler.is_running == True
    
    await market_data_handler.stop()
    mock_websocket_handler.stop.assert_called_once()
    assert market_data_handler.is_running == False

@pytest.mark.asyncio
async def test_subscribe_to_trading_pair(market_data_handler, mock_websocket_handler):
    """Test subscribing to a trading pair"""
    await market_data_handler.start()
    await market_data_handler.subscribe_to_trading_pair("ETH-USD")
    mock_websocket_handler.subscribe.assert_called_with("ETH-USD")
    assert "ETH-USD" in market_data_handler.subscriptions

@pytest.mark.asyncio
async def test_subscribe_when_not_running(market_data_handler, mock_websocket_handler):
    """Test subscribing when the market data handler is not running"""
    await market_data_handler.subscribe_to_trading_pair("ETH-USD")
    mock_websocket_handler.subscribe.assert_not_called()
    assert "ETH-USD" not in market_data_handler.subscriptions


def test_is_data_fresh(market_data_handler):
    """Test checking if market data is fresh"""
    market_data_handler._last_update = datetime.now(timezone.utc)
    assert market_data_handler.is_data_fresh() == True
    
    market_data_handler._last_update = datetime(2023, 1, 1, tzinfo = timezone.utc)
    assert market_data_handler.is_data_fresh() == False
    

def test_get_last_price(market_data_handler):
    """Test getting the last price"""
    market_data_handler.last_prices["BTC-USD"] = 50000.0
    assert market_data_handler.get_last_price("BTC-USD") == 50000.0
    assert market_data_handler.get_last_price("ETH-USD") is None


def test_get_order_book(market_data_handler):
    """Test getting the order book"""
    market_data_handler.order_books["BTC-USD"] = {"bids": {}, "asks": {}}
    assert market_data_handler.get_order_book("BTC-USD") == {"bids": {}, "asks": {}}
    assert market_data_handler.get_order_book("ETH-USD") is None


def test_get_recent_trades(market_data_handler):
    """Test getting recent trades"""
    market_data_handler.trades["BTC-USD"] = [{"time": "12:00", "price": 50000.0, "size": 0.1, "side": "buy"}]
    trades = market_data_handler.get_recent_trades("BTC-USD")
    assert len(trades) == 1
    assert trades[0]['price'] == 50000.0
    assert market_data_handler.get_recent_trades("ETH-USD") == []


def test_handle_ticker_message(market_data_handler):
    """Test handling ticker messages"""
    message = {"type": "ticker", "product_id": "BTC-USD", "price": "50000.0"}
    market_data_handler._handle_message(message)
    assert market_data_handler.last_prices["BTC-USD"] == 50000.0


def test_handle_l2update_message(market_data_handler):
    """Test handling l2update messages"""
    message = {"type": "l2update", "product_id": "BTC-USD", "changes": [["buy", "50000.0", "0.1"]]}
    market_data_handler._handle_message(message)
    assert market_data_handler.order_books["BTC-USD"] == {"bids": {"50000.0": 0.1}, "asks": {}}
    
    message = {"type": "l2update", "product_id": "BTC-USD", "changes": [["sell", "51000.0", "0.2"]]}
    market_data_handler._handle_message(message)
    assert market_data_handler.order_books["BTC-USD"] == {"bids": {"50000.0": 0.1}, "asks": {"51000.0": 0.2}}
    
    # test removal
    message = {"type": "l2update", "product_id": "BTC-USD", "changes": [["buy", "50000.0", "0"]]}
    market_data_handler._handle_message(message)
    assert market_data_handler.order_books["BTC-USD"] == { "bids": {}, "asks": {"51000.0": 0.2}}


def test_handle_match_message(market_data_handler):
    """Test handling match messages"""
    message = {"type": "match", "product_id": "BTC-USD", "price": "50000.0", "size": "0.1", "side": "buy", "time": "12:00"}
    market_data_handler._handle_message(message)
    trades = market_data_handler.trades["BTC-USD"]
    assert len(trades) == 1
    assert trades[0]["price"] == 50000.0
    assert trades[0]["size"] == 0.1
    assert trades[0]["side"] == "buy"


def test_get_market_snapshot(market_data_handler):
    """Test getting the market snapshot"""
    market_data_handler.last_prices["BTC-USD"] = 50000.0
    market_data_handler._last_update = datetime.now(timezone.utc)
    market_data_handler.order_books["BTC-USD"] = {"bids": {"50000.0": 0.1}, "asks": {"51000.0": 0.2}}
    market_data_handler.trades["BTC-USD"] = [{"time": "12:00", "price": 50000.0, "size": 0.1, "side": "buy"}]
    market_data_handler.subscriptions = {"BTC-USD"}
    
    snapshot = market_data_handler.get_market_snapshot("BTC-USD")
    assert snapshot["trading_pair"] == "BTC-USD"
    assert snapshot["last_price"] == 50000.0
    assert snapshot["is_fresh"] == True
    assert snapshot["order_book_depth"] == 1
    assert snapshot["recent_trades_count"] == 1
    assert snapshot['subscribed'] == True