import pytest
import asyncio

@pytest.fixture(scope="function")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def test_config():
    """Provide test configuration for TradingBot."""
    return {
        'trading': {
            'symbols': ['BTC-USD', 'ETH-USD']
        },
        'risk_management': {
            'max_position_size': 10.0,
            'max_daily_loss': 5000.0,
            'stop_loss_pct': 0.05
        },
        'paper_trading': True
    }

def pytest_configure(config):
    config.option.asyncio_mode = "strict"