# Next Thread Prompt: Phase 3 - Core System Test Coverage

## Background
The CryptoJ Trader system has completed Phase 2, establishing a robust paper trading system with comprehensive testing (90% coverage) and integration test infrastructure. Phase 3 focuses on improving test coverage for core system components, particularly targeting the trading core, websocket handler, and market data components that currently have low coverage.

## Current Status

### Coverage Overview
```
Current Coverage Map:
- Overall System: 14% (Target: 85%)
- paper_trading.py: 90% ✓
- order_execution.py: 56%
- exchange_service.py: 40%
- coinbase_api.py: 39%
- market_data.py: 16%
- websocket_handler.py: 9%
- trading_core.py: 0%
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
```

### Current Architecture
```
Trading System
├── TradingCore
│   ├── Order Management
│   ├── Position Tracking
│   └── Risk Management
├── WebSocket Handler
│   ├── Connection Management
│   ├── Market Data Processing
│   └── Order Updates
└── Market Data
    ├── Price Updates
    ├── Order Book
    └── Trade History
```

## Development Priorities

### 1. Core Trading System
- [ ] Trading Core (Target: 60% coverage)
  ```python
  # Key test areas
  class TestTradingCore:
      def test_order_lifecycle()
      def test_position_management()
      def test_risk_calculations()
      def test_emergency_shutdown()
  ```

### 2. WebSocket Implementation
- [ ] WebSocket Handler (Target: 50% coverage)
  ```python
  # Required tests
  class TestWebSocketHandler:
      async def test_connection_management()
      async def test_reconnection_logic()
      async def test_message_processing()
      async def test_subscription_handling()
  ```

### 3. Market Data System
- [ ] Market Data Handler (Target: 50% coverage)
  ```python
  # Test scenarios
  class TestMarketData:
      async def test_price_updates()
      async def test_order_book_updates()
      async def test_trade_history()
      async def test_data_validation()
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
async def websocket_system():
    """Complete WebSocket testing environment"""
    
@pytest.fixture
def market_data_system():
    """Market data testing environment"""
    
@pytest.fixture
def trading_core_system():
    """Trading core testing environment"""
```

### 3. Mock Requirements
```python
# Mock implementations needed
class MockWebSocket:
    async def connect()
    async def disconnect()
    async def send_message()
    
class MockMarketFeed:
    async def subscribe()
    async def get_price()
    async def get_order_book()
```

## Success Criteria

### 1. Coverage Targets
- [ ] Overall system coverage: 50%
- [ ] trading_core.py: 60%
- [ ] websocket_handler.py: 50%
- [ ] market_data.py: 50%

### 2. Test Requirements
- [ ] All core functionality tested
- [ ] Error scenarios covered
- [ ] Edge cases validated
- [ ] Performance benchmarks established

### 3. Quality Metrics
- [ ] All tests passing
- [ ] No critical paths untested
- [ ] Performance within targets
- [ ] Documentation updated

## Available Resources
- Existing test infrastructure
- Mock implementations
- Benchmark utilities
- Coverage reporting tools

## Timeline
Hours 10-12 of 24-hour implementation plan
- Trading core tests: 1 hour
- WebSocket tests: 30 minutes
- Market data tests: 30 minutes

## Notes
1. Focus on critical trading paths
2. Prioritize error scenarios
3. Document performance baselines
4. Consider edge cases
5. Test async behavior thoroughly

Start with implementing core trading system tests, then expand to WebSocket and market data components. Use existing mock system and test utilities to create comprehensive test scenarios.