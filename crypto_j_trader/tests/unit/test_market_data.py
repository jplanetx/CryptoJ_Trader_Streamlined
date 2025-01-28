import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from datetime import datetime
from crypto_j_trader.src.trading.trading_core import get_market_data

@pytest.fixture
def mock_api_response():
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

def test_get_market_data_success(mock_api_response):
    with patch('crypto_j_trader.j_trading.requests.get') as mock_get:
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.json.return_value = mock_api_response
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # Call function
        df = get_market_data("BTC-USD", "1h", 2)
        
        # Verify DataFrame structure
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert list(df.columns) == ['timestamp', 'low', 'high', 'open', 'close', 'volume']
        
        # Verify timestamp handling
        assert isinstance(df.index, pd.DatetimeIndex)
        assert df.index[0] == pd.to_datetime("2025-01-24T00:00:00Z")
        
        # Verify data conversion
        assert df.iloc[0]['close'] == 42400.00
        assert df.iloc[1]['volume'] == 1800000.00

def test_get_market_data_api_error():
    with patch('crypto_j_trader.j_trading.requests.get') as mock_get:
        # Mock API error
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        with pytest.raises(Exception, match="API request failed"):
            get_market_data("BTC-USD", "1h", 2)

def test_get_market_data_invalid_response():
    with patch('crypto_j_trader.j_trading.requests.get') as mock_get:
        # Mock invalid response structure
        mock_response = MagicMock()
        mock_response.json.return_value = {"invalid": "data"}
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        with pytest.raises(Exception, match="Invalid API response"):
            get_market_data("BTC-USD", "1h", 2)
