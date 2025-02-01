"""Test script for EmergencyManager functionality"""
import asyncio
import pandas as pd
from datetime import datetime, timedelta
import json
import os

from crypto_j_trader.src.trading.emergency_manager import EmergencyManager

async def test_emergency_manager():
    """Run comprehensive tests for EmergencyManager"""
    
    # Test configuration
    config = {
        'emergency_price_change_threshold': 0.1,
        'volume_spike_threshold': 5.0,
        'max_data_age_seconds': 300,
        'max_position_close_attempts': 3,
        'position_close_retry_delay': 1,
        'emergency_state_file': 'test_emergency_state.json',
        'default_btc_price': 50000.0,  # Default BTC price for testing
        'risk_management': {
            'position_size_limit': 0.1,  # 10% max position size
            'max_positions': 5
        }
    }
    
    # Initialize EmergencyManager
    em = EmergencyManager(config)
    
    # Ensure we start in non-emergency state
    em.emergency_shutdown = False
    em.shutdown_requested = False
    em.save_state()
    
    print("\nTest 1: Basic Position Validation")
    result = await em.validate_new_position(
        pair="BTC-USD",
        size=1.0,  # 1 BTC position
        portfolio_value=1000000  # $1M portfolio
    )
    print(f"Position validation result: {result}")
    assert result is True, "Basic position validation failed"
    
    # Test 2: Emergency Mode Blocking
    print("\nTest 2: Emergency Mode Blocking")
    em.emergency_shutdown = True
    em.save_state()
    
    result = await em.validate_new_position(
        pair="BTC-USD",
        size=1.0,
        portfolio_value=1000000
    )
    print(f"Position validation in emergency mode: {result}")
    assert result is False, "Emergency mode should block new positions"
    
    # Test 3: Position Size Limit
    print("\nTest 3: Position Size Limit")
    em.emergency_shutdown = False
    em.save_state()
    
    # Test with oversized position (50 BTC ≈ 25% of portfolio)
    result = await em.validate_new_position(
        pair="BTC-USD",
        size=50.0,
        portfolio_value=10000000
    )
    print(f"Large position validation result: {result}")
    assert result is False, "Should reject oversized positions"
    
    # Test 4: Market Data Validation
    print("\nTest 4: Market Data Validation")
    now = datetime.now()
    index = pd.date_range(end=now, periods=10, freq='1min')
    market_data = {
        'BTC-USD': pd.DataFrame({
            'price': [50000] * 10,
            'size': [100] * 10
        }, index=index)
    }
    
    # Test with normal size position with market data
    result = await em.validate_new_position(
        pair="BTC-USD",
        size=1.0,  # 1 BTC
        portfolio_value=1000000,  # $1M portfolio
        market_data=market_data
    )
    print(f"Position validation with market data: {result}")
    assert result is True, "Market data validation failed"
    
    # Test 4.1: Market Data with Price Movement
    market_data['BTC-USD'].iloc[-1, market_data['BTC-USD'].columns.get_loc('price')] = 60000  # 20% price increase
    result = await em.validate_new_position(
        pair="BTC-USD",
        size=1.0,
        portfolio_value=1000000,
        market_data=market_data
    )
    print(f"Position validation with price movement: {result}")
    assert result is False, "Should reject on large price movement"
    
    # Test 5: State Persistence
    print("\nTest 5: State Persistence")
    em.emergency_shutdown = True
    em.save_state()
    
    # Verify file exists and content is correct
    assert os.path.exists(config['emergency_state_file']), "State file not created"
    with open(config['emergency_state_file'], 'r') as f:
        state = json.load(f)
        print(f"State file content: {json.dumps(state, indent=2)}")
        assert state['emergency_shutdown'] is True, "State not saved correctly"
    
    print(f"State file created and verified: {config['emergency_state_file']}")
    
    # Test 6: System Health Checks
    print("\nTest 6: System Health Checks")
    health = em.get_system_health()
    print(f"System health status: {json.dumps(health, indent=2)}")
    assert 'emergency_mode' in health, "Health check missing emergency mode"
    assert 'system_checks' in health, "Health check missing system checks"
    
    # Reset state before edge cases
    em.reset_emergency_state()
    
    # Test 7: Position Size Edge Cases
    print("\nTest 7: Position Size Edge Cases")
    
    # Test with exactly 10% position size (20 BTC = $1M = 10% of $10M at $50k/BTC)
    result = await em.validate_new_position(
        pair="BTC-USD",
        size=20.0,
        portfolio_value=10000000
    )
    print(f"Exact limit position validation result: {result}")
    assert result is True, "Should accept position at exact limit"
    
    # Test with slightly over 10% (21 BTC ≈ 10.5% of portfolio)
    result = await em.validate_new_position(
        pair="BTC-USD",
        size=21.0,
        portfolio_value=10000000
    )
    print(f"Over limit position validation result: {result}")
    assert result is False, "Should reject position slightly over limit"
    
    # Cleanup
    if os.path.exists(config['emergency_state_file']):
        os.remove(config['emergency_state_file'])
    
    print("\nAll tests completed successfully!")

if __name__ == "__main__":
    asyncio.run(test_emergency_manager())