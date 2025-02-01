# Integration Tests Implementation

## New Integration Tests Added

### 1. Risk Management and Emergency Manager Integration
```python
@pytest.mark.asyncio
async def test_risk_emergency_integration():
    # Setup
    risk_manager = RiskManager(config={'max_position_size': 1.0})
    emergency_manager = EmergencyManager(risk_manager)
    
    # Test emergency mode activation on risk threshold breach
    await risk_manager.assess_risk({'position_size': 2.0})
    assert emergency_manager.is_emergency_mode_active()
    
    # Test position validation during emergency
    result = await emergency_manager.validate_new_position(size=0.5)
    assert result['status'] == 'error'
    assert 'emergency mode' in result['error'].lower()
```

### 2. Order Execution with Risk Validation
```python
@pytest.mark.asyncio
async def test_order_execution_risk_validation():
    # Setup
    order_executor = OrderExecutor(risk_manager=risk_manager)
    
    # Test order rejection on risk limit breach
    order = {
        'symbol': 'BTC-USD',
        'size': 2.0,
        'side': 'buy'
    }
    
    result = await order_executor.execute_order(order)
    assert result['status'] == 'error'
    assert 'risk limit exceeded' in result['error'].lower()
```

### 3. System Health Integration
```python
@pytest.mark.asyncio
async def test_system_health_integration():
    # Setup
    health_monitor = HealthMonitor()
    risk_manager = RiskManager(health_monitor=health_monitor)
    
    # Test system health impact on risk assessment
    health_monitor.set_unhealthy('market_data_stale')
    result = await risk_manager.assess_risk({'position_size': 0.1})
    assert result['status'] == 'error'
    assert 'system unhealthy' in result['error'].lower()
```

## Health Check Integration
```python
@pytest.mark.asyncio
async def test_health_check_integration():
    # Setup
    ws_handler = WebSocketHandler()
    health_monitor = HealthMonitor(ws_handler)
    
    # Test websocket disconnection impact
    await ws_handler.disconnect()
    health_status = await health_monitor.check_health()
    assert health_status['status'] == 'unhealthy'
    assert 'websocket disconnected' in health_status['details'].lower()
```

## Remaining Tasks

1. Emergency Manager Updates
   - Implement missing validate_new_position method
   - Fix JSON persistence issues
   - Resolve state inconsistencies

2. WebSocket Handler
   - Add reconnection logic
   - Implement subscription management
   - Add message handling

3. System Health Monitoring
   - Add latency checks
   - Implement threshold monitoring
   - Add health status comparison

## Next Steps
1. Complete Emergency Manager implementation
2. Add WebSocket handler updates
3. Implement remaining health monitoring features

## Notes
- Integration tests added to test_trading_core.py
- Created new test fixtures in conftest.py
- Updated mock objects for testing
- Added comprehensive error handling