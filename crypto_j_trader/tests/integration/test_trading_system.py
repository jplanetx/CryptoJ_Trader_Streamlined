"""Integration tests for complete trading system."""
import pytest
import pytest_asyncio
import asyncio
from datetime import datetime, timezone
from crypto_j_trader.src.trading.trading_core import TradingBot
from crypto_j_trader.src.trading.health_monitor import HealthMonitor
from crypto_j_trader.src.trading.position_manager import PositionManager

@pytest.fixture
def test_config():
    return {
        'trading_pairs': ['BTC-USD', 'ETH-USD'],
        'risk_management': {
            'stop_loss_pct': 0.05,
            'max_position_size': 20.0,
            'max_daily_loss': 1000.0,
            'max_position_loss': 500.0
        },
        'paper_trading': True,
        'position_limits': {
            'max_position_value': 10000.0,
            'max_leverage': 3.0,
            'min_position_size': 0.001
        },
        'take_profit_levels': [
            {'pct': 0.05, 'size': 0.3},
            {'pct': 0.10, 'size': 0.5}
        ],
        'detailed_health_check': True
    }

@pytest_asyncio.fixture
async def trading_components(test_config):
    """Create individual trading system components."""
    bot = TradingBot(test_config)
    health_monitor = HealthMonitor()
    position_manager = PositionManager(test_config)
    return bot, health_monitor, position_manager

class TestTradingSystem:
    @pytest.mark.asyncio
    async def test_complete_trading_cycle(self, trading_components):
        """Test a complete trading cycle with all components."""
        bot, health_monitor, position_manager = trading_components
        trading_pair = 'BTC-USD'
        
        # 1. System health check
        health_status = await bot.check_health()
        assert isinstance(health_status, dict)
        assert health_status['status'] == 'healthy'

        # 2. Market data update
        await bot.update_market_price(trading_pair, 50000.0)
        assert trading_pair in bot.market_prices
        
        # 3. Position sizing
        account_value = 100000.0
        volatility = position_manager.calculate_volatility(
            trading_pair,
            [50000.0 * (1 + 0.001 * i) for i in range(30)]
        )
        size = position_manager.calculate_position_size(
            trading_pair,
            account_value,
            50000.0,
            volatility
        )
        assert size > 0

        # 4. Risk validation
        risk_check = position_manager.validate_position_risk(
            trading_pair,
            size,
            50000.0,
            account_value
        )
        assert risk_check['valid']

        # 5. Order execution
        start_time = datetime.now(timezone.utc).timestamp()
        order_result = await bot.execute_order('buy', size, 50000.0, trading_pair)
        delay = health_monitor.record_order_latency(start_time)
        assert order_result['status'] == 'success'
        assert delay > 0

        # 6. Position monitoring
        position = await bot.get_position(trading_pair)
        assert position['size'] == size
        assert position['entry_price'] == 50000.0

        # 7. Take profit setup
        take_profit = position_manager.calculate_dynamic_take_profit(
            trading_pair,
            50000.0,
            size,
            volatility
        )
        assert len(take_profit['levels']) > 0

        # 8. Market movement simulation
        await bot.update_market_price(trading_pair, 52500.0)  # 5% profit
        updated_position = await bot.get_position(trading_pair)
        assert updated_position['unrealized_pnl'] > 0

        # 9. System health check during operation
        health = await bot.check_health()
        assert health['status'] in ['healthy', 'degraded']
        
        # 10. Position closing
        close_result = await bot.execute_order('sell', size, 52500.0, trading_pair)
        assert close_result['status'] == 'success'
        
        final_position = await bot.get_position(trading_pair)
        assert final_position['size'] == 0.0

    @pytest.mark.asyncio
    async def test_emergency_procedures(self, trading_components):
        """Test emergency procedures and system recovery."""
        bot, health_monitor, position_manager = trading_components
        trading_pair = 'BTC-USD'

        # 1. Setup initial position
        size = 1.0
        entry_price = 50000.0
        await bot.execute_order('buy', size, entry_price, trading_pair)

        # 2. Simulate market crash (10% drop)
        crash_price = entry_price * 0.90
        await bot.update_market_price(trading_pair, crash_price)

        # 3. Verify emergency shutdown triggered
        assert len(bot.positions) == 0  # All positions should be closed

        # 4. Check system status
        health_status = await bot.check_health()
        assert health_status['status'] != 'healthy'
        assert not bot.is_healthy

    @pytest.mark.asyncio
    async def test_multi_position_management(self, trading_components):
        """Test managing multiple positions simultaneously."""
        bot, health_monitor, position_manager = trading_components
        
        # 1. Open positions in different pairs
        positions_data = [
            ('BTC-USD', 1.0, 50000.0),
            ('ETH-USD', 10.0, 3000.0)
        ]

        # Open positions
        for pair, size, price in positions_data:
            result = await bot.execute_order('buy', size, price, pair)
            assert result['status'] == 'success'
            
            position = await bot.get_position(pair)
            assert position['size'] == size
            assert position['entry_price'] == price

        # 2. Update market prices (5% increase)
        price_updates = [
            ('BTC-USD', 52500.0),
            ('ETH-USD', 3150.0)
        ]

        for pair, price in price_updates:
            await bot.update_market_price(pair, price)
            position = await bot.get_position(pair)
            assert position['unrealized_pnl'] > 0

        # 3. Close all positions
        for pair, size, _ in positions_data:
            current_pos = await bot.get_position(pair)
            if current_pos['size'] > 0:
                close_price = bot.market_prices[pair]
                result = await bot.execute_order('sell', abs(current_pos['size']), close_price, pair)
                assert result['status'] == 'success'

        # 4. Verify all positions closed
        for pair, _, _ in positions_data:
            position = await bot.get_position(pair)
            assert position['size'] == 0.0

    @pytest.mark.asyncio
    async def test_risk_management_integration(self, trading_components):
        """Test integrated risk management features."""
        bot, health_monitor, position_manager = trading_components

        # 1. Test position size limits
        large_size = 100.0  # Very large position
        result = await bot.execute_order('buy', large_size, 50000.0, 'BTC-USD')
        assert result['status'] == 'error'

        # 2. Test daily loss limits
        bot.daily_loss = bot.config['risk_management']['max_daily_loss'] + 1
        result = await bot.execute_order('buy', 1.0, 50000.0, 'BTC-USD')
        assert result['status'] == 'error'
        assert 'Daily loss limit' in result['message']

        # 3. Reset daily loss
        bot.daily_loss = 0.0
        
        # Test position sizing
        size = position_manager.calculate_position_size(
            'BTC-USD',
            100000.0,  # Account value
            50000.0,   # Current price
            0.5        # Volatility
        )
        assert size > 0
        assert size * 50000.0 <= bot.config['position_limits']['max_position_value']

        # 4. Test exposure limits
        positions_to_open = [
            ('BTC-USD', 1.0, 50000.0),
            ('ETH-USD', 10.0, 3000.0),
            ('XRP-USD', 1000.0, 1.0)  # Should fail due to max positions
        ]

        opened_positions = 0
        for pair, size, price in positions_to_open:
            result = await bot.execute_order('buy', size, price, pair)
            if result['status'] == 'success':
                opened_positions += 1

        assert opened_positions <= bot.config.get('max_concurrent_positions', 2)

    @pytest.mark.asyncio
    async def test_system_performance_monitoring(self, trading_components):
        """Test system performance monitoring and metrics collection."""
        bot, health_monitor, position_manager = trading_components

        # 1. Monitor order execution performance
        start_time = datetime.now(timezone.utc).timestamp()
        await bot.execute_order('buy', 1.0, 50000.0, 'BTC-USD')
        latency = health_monitor.record_order_latency(start_time)
        assert isinstance(latency, float)

        # 2. System health metrics
        health_metrics = await bot.check_health()
        assert isinstance(health_metrics, dict)
        assert 'metrics' in health_metrics
        assert 'status' in health_metrics

        # 3. Performance metrics
        perf_metrics = health_monitor.get_performance_metrics()
        assert isinstance(perf_metrics, dict)
        assert 'current' in perf_metrics
        assert 'averages' in perf_metrics
