"""Integration tests for full trading workflow"""
import pytest
import asyncio
from crypto_j_trader.src.trading.trading_core import TradingBot
from crypto_j_trader.src.trading.websocket_handler import WebSocketHandler
from crypto_j_trader.src.utils.monitoring import TradingMonitor
import logging
import json

@pytest.fixture
def test_config():
    """Test configuration with paper trading enabled"""
    return {
        "paper_trading": True,
        "initial_capital": 10000,
        "target_capital": 20000,
        "days_target": 30,
        "trading_pairs": [
            {"pair": "BTC-USD", "weight": 0.6},
            {"pair": "ETH-USD", "weight": 0.4}
        ],
        "strategy": {
            "rsi_period": 14,
            "ma_short": 10,
            "ma_long": 20
        },
        "execution": {
            "interval_seconds": 300
        },
        "risk_management": {
            "max_position_size": 0.1,
            "stop_loss_pct": 0.05,
            "daily_loss_limit_pct": 0.02
        },
        "websocket": {
            "enabled": True,
            "heartbeat_interval_seconds": 30
        }
    }

@pytest.fixture
async def trading_bot(test_config, tmp_path):
    """Initialize trading bot with test configuration"""
    config_path = tmp_path / "test_config.json"
    with open(config_path, "w") as f:
        json.dump(test_config, f)
    
    bot = TradingBot(config_path=str(config_path))
    yield bot
    # Cleanup
    if bot.websocket_handler:
        await bot.websocket_handler.stop()

@pytest.mark.asyncio
async def test_trading_initialization(trading_bot):
    """Test trading bot initialization and components setup"""
    assert trading_bot.config["paper_trading"] is True
    assert isinstance(trading_bot.websocket_handler, WebSocketHandler)
    assert isinstance(trading_bot.monitor, TradingMonitor)
    assert len(trading_bot.strategies) == len(trading_bot.config["trading_pairs"])

@pytest.mark.asyncio
async def test_market_data_retrieval(trading_bot):
    """Test market data fetching and processing"""
    if trading_bot.websocket_handler:
        await trading_bot.websocket_handler.start()
        await asyncio.sleep(5)  # Wait for initial data
        
        # Verify WebSocket connection
        assert trading_bot.websocket_handler.is_running
        assert trading_bot._validate_websocket_state()
        
        # Check market data
        assert len(trading_bot.market_data) > 0
        for pair in trading_bot.config["trading_pairs"]:
            assert pair["pair"] in trading_bot.market_data

@pytest.mark.asyncio
async def test_risk_management_limits(trading_bot):
    """Test risk management constraints"""
    # Verify position size limits
    max_position = trading_bot.config["risk_management"]["max_position_size"]
    total_capital = trading_bot.config["initial_capital"]
    
    for pair in trading_bot.config["trading_pairs"]:
        max_allowed = total_capital * max_position
        position_size = trading_bot.risk_manager.calculate_position_size(
            pair["pair"],
            total_capital,
            1.0  # Current price placeholder
        )
        assert position_size <= max_allowed

@pytest.mark.asyncio
async def test_emergency_shutdown(trading_bot):
    """Test emergency shutdown procedure"""
    # Simulate emergency condition
    await trading_bot._initiate_emergency_shutdown()
    
    assert trading_bot.emergency_shutdown is True
    assert trading_bot.shutdown_requested is True
    
    if trading_bot.websocket_handler:
        assert not trading_bot.websocket_handler.is_running

@pytest.mark.asyncio
async def test_system_health_monitoring(trading_bot):
    """Test system health checks"""
    # Initial health check should pass
    assert trading_bot._check_system_health()
    
    # Simulate WebSocket disconnection
    if trading_bot.websocket_handler:
        await trading_bot.websocket_handler.stop()
        await asyncio.sleep(1)
        
        # Health check should fail with WebSocket disabled
        if trading_bot.config["websocket"]["enabled"]:
            assert not trading_bot._check_system_health()

@pytest.mark.asyncio
async def test_trading_loop_execution(trading_bot):
    """Test main trading loop execution"""
    # Start trading loop
    loop_task = asyncio.create_task(trading_bot.run_trading_loop())
    
    # Let it run briefly
    await asyncio.sleep(10)
    
    # Request shutdown
    trading_bot.shutdown_requested = True
    await asyncio.sleep(1)
    
    # Verify clean shutdown
    await loop_task
    assert not trading_bot.websocket_handler or not trading_bot.websocket_handler.is_running