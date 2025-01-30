"""Tests for market data functionality."""
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from datetime import datetime
from crypto_j_trader.src.trading.market_data import MarketData

@pytest.fixture
def market_data():
    # Use paper_trading=False so that tests go through the real code path (with mocked requests).
    return MarketData(api_url="https://mockapi.test", paper_trading=False)

@pytest.fixture
def mock_candle_response():
    return {
        "candles": [
            {
                "start": "2025-01-24T00:00:00Z",
                "low": "42000.00",
                "high": "42500.00",
                "open": "42100.00",
                "close": "42400.00",
                "volume": "1500000.00"
            },
            {
                "start": "2025-01-24T01:00:00Z",
                "low": "42200.00",
                "high": "42700.00",
                "open": "42300.00",
                "close": "42600.00",
                "volume": "1800000.00"
            }
        ]
    }

@pytest.fixture
def mock_ticker_response():
    return {
        "price": "42500.00",
        "volume_24h": "15000000.00",
        "low_24h": "41800.00",
        "high_24h": "42900.00",
        "time": "2025-01-24T02:00:00Z"
    }

def test_get_market_data_success(market_data, mock_candle_response):
    """Test successful market data retrieval"""
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.json.return_value = mock_candle_response
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        df = market_data.get_market_data("BTC-USD", "1h", 2)
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert list(df.columns) == ['low', 'high', 'open', 'close', 'volume']
        assert pd.api.types.is_float_dtype(df['close'])
        assert df.iloc[0]['close'] == 42400.00
        assert df.iloc[1]['volume'] == 1800000.00

def test_get_market_data_api_error(market_data):
    """Test API error handling"""
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_get.return_value = mock_response

        with pytest.raises(Exception, match="API request failed"):
            market_data.get_market_data("BTC-USD", "1h", 2)

def test_get_market_data_invalid_response(market_data):
    """Test invalid API response handling"""
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.json.return_value = {"invalid": "data"}
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        with pytest.raises(Exception, match="Invalid API response"):
            market_data.get_market_data("BTC-USD", "1h", 2)

def test_get_ticker_success(market_data, mock_ticker_response):
    """Test successful ticker retrieval"""
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.json.return_value = mock_ticker_response
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        ticker = market_data.get_ticker("BTC-USD")
        
        assert isinstance(ticker, dict)
        assert ticker['price'] == 42500.00
        assert ticker['volume_24h'] == 15000000.00
        assert ticker['low_24h'] == 41800.00
        assert ticker['high_24h'] == 42900.00
        assert isinstance(ticker['timestamp'], pd.Timestamp)

def test_get_ticker_api_error(market_data):
    """Test ticker API error handling"""
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_get.return_value = mock_response

        with pytest.raises(Exception, match="API request failed"):
            market_data.get_ticker("BTC-USD")

def test_aggregate_market_data_success(market_data, mock_candle_response):
    """Test successful aggregate market data retrieval"""
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.json.return_value = mock_candle_response
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        pairs = ["BTC-USD", "ETH-USD"]
        result = market_data.aggregate_market_data(pairs)
        
        assert isinstance(result, dict)
        assert len(result) == 2
        assert all(isinstance(df, pd.DataFrame) for df in result.values())
        assert all(pair in result for pair in pairs)

def test_aggregate_market_data_partial_failure(market_data, mock_candle_response):
    """Test partial failure in aggregate market data retrieval"""
    with patch('requests.get') as mock_get:
        def mock_get_side_effect(*args, **kwargs):
            mock_success = MagicMock()
            mock_success.json.return_value = mock_candle_response
            mock_success.status_code = 200
            
            mock_error = MagicMock()
            mock_error.status_code = 500
            mock_error.text = "Internal Server Error"
            
            if "BTC-USD" in args[0]:
                return mock_success
            return mock_error
            
        mock_get.side_effect = mock_get_side_effect

        pairs = ["BTC-USD", "ETH-USD"]
        result = market_data.aggregate_market_data(pairs)
        
        assert isinstance(result, dict)
        assert len(result) == 2
        assert not result["ETH-USD"].empty
        assert len(result["BTC-USD"]) == 2

def test_invalid_granularity(market_data):
    """Test invalid granularity handling"""
    with pytest.raises(ValueError, match="Invalid granularity"):
        market_data.get_market_data("BTC-USD", "invalid")

def test_empty_response_handling(market_data):
    """Test empty candles response handling"""
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.json.return_value = {"candles": []}
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        df = market_data.get_market_data("BTC-USD")
        assert isinstance(df, pd.DataFrame)
        assert df.empty
        assert list(df.columns) == ['low', 'high', 'open', 'close', 'volume']
