import pytest
from crypto_j_trader.src.trading.order_execution import OrderExecution
from crypto_j_trader.src.trading.trading_core import TradingCore

@pytest.fixture
def trading_core():
    return TradingCore()

def test_order_execution_success(trading_core):
    """
    Test that an order is executed successfully.
    """
    order = {"symbol": "ETHUSD", "quantity": 2, "price": 3000}
    result = trading_core.execute_order(order)
    assert result["status"] == "success"
    assert "order_id" in result

def test_order_execution_insufficient_funds(trading_core):
    """
    Test that executing an order with insufficient funds raises an error.
    """
    order = {"symbol": "ETHUSD", "quantity": 1000, "price": 3000}
    with pytest.raises(ValueError):
        trading_core.execute_order(order)