import pytest
import pytest_asyncio
import asyncio

class DummyTradingCore:
    """
    Dummy Trading Core to simulate order management, position tracking,
    risk calculations, and emergency shutdown for testing purposes.
    """
    def __init__(self):
        self.orders = []
        self.positions = {}
        self.emergency = False

    async def place_order(self, order):
        # Simulate placing an order.
        await asyncio.sleep(0.05)
        self.orders.append(order)
        return order

    async def cancel_order(self, order_id):
        # Simulate canceling an order by order_id.
        await asyncio.sleep(0.05)
        self.orders = [o for o in self.orders if o.get("id") != order_id]
        return True

    async def manage_position(self, symbol, quantity):
        # Simulate updating the position for a given symbol.
        await asyncio.sleep(0.05)
        self.positions[symbol] = self.positions.get(symbol, 0) + quantity
        return self.positions[symbol]

    async def calculate_risk(self):
        # Dummy risk calculation: sum of absolute position quantities.
        await asyncio.sleep(0.05)
        return sum(abs(qty) for qty in self.positions.values())

    async def emergency_shutdown(self):
        # Simulate emergency shutdown: clear orders and positions, set emergency flag.
        await asyncio.sleep(0.05)
        self.orders = []
        self.positions = {}
        self.emergency = True
        return True

@pytest_asyncio.fixture
async def trading_core_system():
    """Fixture providing a dummy Trading Core system for testing."""
    return DummyTradingCore()

class TestTradingCore:
    @pytest.mark.asyncio
    async def test_order_lifecycle(self, trading_core_system):
        # Test the order lifecycle: placing and canceling an order.
        order = {"id": 1, "symbol": "BTC", "quantity": 0.5}
        placed_order = await trading_core_system.place_order(order)
        assert placed_order == order, "Order should be placed successfully."
        assert order in trading_core_system.orders, "Order should be recorded in orders list."
        result = await trading_core_system.cancel_order(order_id=1)
        assert result is True, "Order cancellation should return True."
        assert order not in trading_core_system.orders, "Order should be removed from orders list after cancellation."

    @pytest.mark.asyncio
    async def test_position_management(self, trading_core_system):
        # Test updating and managing positions.
        updated_position = await trading_core_system.manage_position("BTC", 1)
        assert updated_position == 1, "Position should be updated correctly for BTC."
        updated_position = await trading_core_system.manage_position("BTC", -0.5)
        assert updated_position == 0.5, "Position should be adjusted correctly for BTC."

    @pytest.mark.asyncio
    async def test_risk_calculations(self, trading_core_system):
        # Test risk calculation based on current positions.
        await trading_core_system.manage_position("BTC", 2)
        await trading_core_system.manage_position("ETH", -3)
        risk = await trading_core_system.calculate_risk()
        assert risk == 5, "Risk should be the sum of absolute position quantities (2 + 3)."

    @pytest.mark.asyncio
    async def test_emergency_shutdown(self, trading_core_system):
        # Test emergency shutdown functionality.
        order = {"id": 2, "symbol": "ETH", "quantity": 1}
        await trading_core_system.place_order(order)
        await trading_core_system.manage_position("ETH", 1)
        shutdown_result = await trading_core_system.emergency_shutdown()
        assert shutdown_result is True, "Emergency shutdown should return True."
        assert trading_core_system.orders == [], "Orders list should be cleared after emergency shutdown."
        assert trading_core_system.positions == {}, "Positions should be cleared after emergency shutdown."
        assert trading_core_system.emergency is True, "Emergency flag should be set to True after emergency shutdown."