import os
import pytest
from unittest.mock import patch, MagicMock
from crypto_j_trader.src.main import TradingBot

@pytest.fixture
def mock_env_vars(monkeypatch):
    monkeypatch.setenv("TESTING", "true")

@patch('crypto_j_trader.src.main.RESTClient')
def test_setup_client(mock_rest_client, mock_env_vars):
    mock_client_instance = MagicMock()
    mock_rest_client.return_value = mock_client_instance
    mock_client_instance.get_accounts.return_value = MagicMock(accounts=True)

    bot = TradingBot()
    client = bot.client

    assert client == mock_client_instance
    mock_rest_client.assert_called_once_with(api_key="test_api_key", api_secret="test_api_secret")
    mock_client_instance.get_accounts.assert_called_once()

@patch('crypto_j_trader.src.main.RESTClient')
def test_setup_client_missing_env_vars(mock_rest_client, monkeypatch):
    monkeypatch.delenv("TESTING", raising=False)
    monkeypatch.delenv("COINBASE_API_KEY", raising=False)
    monkeypatch.delenv("COINBASE_API_SECRET", raising=False)

    with pytest.raises(ValueError, match="Missing API key or secret in environment variables"):
        bot = TradingBot()

@patch('crypto_j_trader.src.main.RESTClient')
def test_run(mock_rest_client, mock_env_vars):
    mock_client_instance = MagicMock()
    mock_rest_client.return_value = mock_client_instance
    mock_client_instance.get_accounts.return_value = MagicMock(accounts=True)

    bot = TradingBot()
    bot._setup_client = MagicMock(return_value=mock_client_instance)
    bot.paper_trader = MagicMock()

    bot.run()

    bot.paper_trader.place_order.assert_called_once_with({
        "symbol": bot.config['trading_pair'],
        "side": "buy",
        "quantity": 0.001,
        "type": "market"
    })
