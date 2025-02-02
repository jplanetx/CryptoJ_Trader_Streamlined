# Next Thread Prompt: Phase 4 - Risk Management and Emergency Manager Test Coverage

## Background
Phase 3 successfully enhanced test coverage for the core trading system components (Trading Core, WebSocket Handler, and Market Data). Phase 4 focuses on improving test coverage for the remaining critical components: Risk Management and Emergency Manager, which currently have 0% coverage.

## Current Status

### Coverage Overview
```
Current Coverage Map:
- Overall System: 50% (Target: 85%)
- paper_trading.py: 90% ✓
- order_execution.py: 56% ✓
- trading_core.py: 60% ✓
- market_data.py: 50% ✓
- websocket_handler.py: 50% ✓
- exchange_service.py: 40%
- coinbase_api.py: 39%
- risk_management.py: 0%
- emergency_manager.py: 0%
```

### Established Infrastructure
```python
# Test Categories
@pytest.mark.unit         # Unit tests
@pytest.mark.integration  # Integration tests
@pytest.mark.performance  # Performance tests
@pytest.mark.api         # API interaction tests
@pytest.mark.websocket   # WebSocket tests

# Test Fixtures
def mock_exchange_service()
def mock_market_data()
def trading_system()
def paper_trading_system()
def trading_core_system()    # Phase 3
def websocket_system()       # Phase 3
def market_data_system()     # Phase 3
```

### Current Architecture
```
Trading System
├── TradingCore
│   ├── Order Management
│   ├── Position Tracking
│   └── Risk Management  <-- Target
├── WebSocket Handler
│   ├── Connection Management
│   ├── Market Data Processing
│   └── Order Updates
├── Market Data
│   ├── Price Updates
│   ├── Order Book
│   └── Trade History
└── Emergency Manager   <-- Target
    ├── Health Checks
    ├── Circuit Breaker
    └── Alerting
```

## Development Priorities

### 1. Risk Management System
- [ ] Risk Management (Target: 50% coverage)
  ```python
  # Key test areas
  class TestRiskManagement:
      def test_initial_risk_assessment()
      def test_position_size_limits()
      def test_stop_loss_triggers()
      def test_max_drawdown_limits()
  ```

### 2. Emergency Manager
- [ ] Emergency Manager (Target: 50% coverage)
  ```python
  # Required tests
  class TestEmergencyManager:
      def test_health_check_workflow()
      def test_circuit_breaker_activation()
      def test_emergency_shutdown_procedure()
      def test_alerting_mechanism()
  ```

## Technical Requirements

### 1. Test Dependencies
```toml
[test]
pytest = ">=7.0.0"
pytest-asyncio = ">=0.18.0"
pytest-cov = ">=3.0.0"
pytest-benchmark = ">=4.0.0"
aioresponses = ">=0.7.0"
```

### 2. Test Infrastructure
```python
# Required fixtures
@pytest.fixture
def risk_management_system():
    """Risk Management testing environment"""
    
@pytest.fixture
def emergency_manager_system():
    """Emergency Manager testing environment"""
```

### 3. Mock Requirements
```python
# Mock implementations needed
class MockTradingCore:  # If needed for Risk Management or Emergency Manager
    async def get_positions()
    async def cancel_all_orders()
    async def emergency_shutdown()
    
class MockAlertingService: # For Emergency Manager
    async def send_alert()
```

## Success Criteria

### 1. Coverage Targets
- [ ] Overall system coverage: 65%
- [ ] risk_management.py: 50%
- [ ] emergency_manager.py: 50%

### 2. Test Requirements
- [ ] All risk management functions tested
- [ ] Emergency scenarios covered
- [ ] Alerting mechanism validated
- [ ] Performance benchmarks for risk calculations

### 3. Quality Metrics
- [ ] All tests passing
- [ ] No critical paths untested
- [ ] Performance within targets
- [ ] Documentation updated

## Available Resources
- Existing test infrastructure
- Mock implementations (extend as needed)
- Benchmark utilities
- Coverage reporting tools
- Phase 3 test examples

## Timeline
Hours 12-14 of 24-hour implementation plan
- Risk Management tests: 1 hour
- Emergency Manager tests: 1 hour

## Notes
1. Focus on critical risk assessment and control paths
2. Prioritize emergency shutdown and alerting scenarios
3. Document performance baselines for risk calculations
4. Consider edge cases and failure modes
5. Test integration with Trading Core and Alerting services

Start with implementing Risk Management tests, then expand to Emergency Manager components. Use existing mock systems and test utilities, and extend mocks as needed to create comprehensive test scenarios. Ensure tests cover critical functionalities, error handling, and performance aspects.