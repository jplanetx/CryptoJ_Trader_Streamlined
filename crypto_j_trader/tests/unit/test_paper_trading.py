import pytest
from crypto_j_trader.src.trading.paper_trading import PaperTrader
from crypto_j_trader.src.trading.order_execution import OrderExecution

# Dummy class to simulate order execution behavior
class DummyOrderExecution(OrderExecution):
    def execute_order(self, order):
        # simulate a successful order execution
        return {"status": "filled", "order_id": 123}

@pytest.fixture
def paper_trader():
    # Initialize PaperTrader with a dummy order executor
    executor = DummyOrderExecution()
    trader = PaperTrader(executor)
    return trader

def test_place_order_success(paper_trader):
    order = {"symbol": "BTCUSD", "quantity": 1, "price": 10000, "side": "buy"}
    result = paper_trader.place_order(order)
    assert result["status"] == "filled"
    assert "order_id" in result

def test_place_order_failure(paper_trader, monkeypatch):
    # Simulate a failure in order execution
    def failing_execute_order(order):
        raise Exception("Order execution failed")
    monkeypatch.setattr(paper_trader.order_executor, "execute_order", failing_execute_order)
    order = {"symbol": "BTCUSD", "quantity": 1, "price": 10000, "side": "sell"}
    with pytest.raises(Exception) as exc_info:
        paper_trader.place_order(order)
    assert "Order execution failed" in str(exc_info.value)