# CryptoJ Trader Testing Guide

## Testing Infrastructure

The testing infrastructure has been organized to support different types of tests:

- Unit tests (`tests/unit/`)
- Integration tests (`tests/integration/`)
- End-to-end tests (`tests/e2e/`)
- Performance tests (`tests/performance/`)

### Directory Structure

```
crypto_j_trader/tests/
├── utils/
│   ├── fixtures/       # Reusable test fixtures
│   ├── helpers/        # Test helper functions
│   └── mocks/          # Mock objects and responses
├── unit/              # Unit tests
├── integration/       # Integration tests
└── e2e/              # End-to-end tests
```

## Test Utilities

### Async Testing

```python
from crypto_j_trader.tests.utils import async_test, async_timeout

@async_test
async def test_async_function():
    async with async_timeout():
        # Your async test code here
        pass
```

### Test Fixtures

```python
from crypto_j_trader.tests.utils import (
    test_config,
    mock_market_data,
    mock_account_balance
)

def test_with_fixtures(test_config, mock_market_data):
    # Access test configuration and mock data
    assert test_config['trading']['symbols'] == ['BTC-USD', 'ETH-USD']
```

### API Mocks

```python
from crypto_j_trader.tests.utils import MockCoinbaseResponses

def test_api_interaction():
    mock_response = MockCoinbaseResponses.get_product('BTC-USD')
    # Use mock response in tests
```

## Running Tests

Use the test runner script to execute different types of tests:

```bash
# Run all tests
python scripts/run_tests.py

# Run specific test types
python scripts/run_tests.py --type unit
python scripts/run_tests.py --type integration
python scripts/run_tests.py --type e2e
python scripts/run_tests.py --type performance

# Run with verbose output
python scripts/run_tests.py -v

# Run without coverage
python scripts/run_tests.py --no-coverage
```

## Test Markers

Use pytest markers to categorize tests:

```python
@pytest.mark.unit
def test_unit_functionality():
    pass

@pytest.mark.integration
def test_integration_workflow():
    pass

@pytest.mark.e2e
def test_end_to_end_scenario():
    pass

@pytest.mark.performance
def test_performance_benchmark():
    pass
```

## Core Component Testing

### Trading Core Tests

The `test_trading_core.py` file in `tests/unit/` directory contains unit tests for the Trading Core component.
These tests cover critical functionalities such as:

- Order lifecycle management (placing, canceling orders)
- Position management (updating and adjusting positions)
- Risk calculations (assessing risk based on positions)
- Emergency shutdown procedures

Example test structure:

```python
@pytest.mark.asyncio
async def test_order_lifecycle(trading_core_system):
    # Test order placement and cancellation
    order = {"id": 1, "symbol": "BTC", "quantity": 0.5}
    placed_order = await trading_core_system.place_order(order)
    assert placed_order == order
    # ... (rest of the test)
```

### WebSocket Handler Tests

The `test_websocket_handler.py` file in `tests/unit/` directory includes unit tests for the WebSocket Handler component.
These tests validate:

- Connection management (connect, disconnect)
- Reconnection logic (automatic reconnection attempts)
- Message processing (sending and receiving messages)
- Subscription handling (subscribing to channels)

Example test structure:

```python
@pytest.mark.asyncio
async def test_connection_management(websocket_system):
    # Test WebSocket connection and disconnection
    connected = await websocket_system.connect()
    assert connected
    # ... (rest of the test)
```

### Position Tracking Tests

Position tracking tests need to handle both paper trading and live trading position formats:

```python
@pytest.mark.unit
async def test_position_tracking():
    # Test position in paper trading mode
    paper_position = await trading_system.get_position("BTC-USD")
    if isinstance(paper_position, dict):
        # Live trading format
        assert Decimal(str(paper_position['size'])) == Decimal('1.0')
        assert Decimal(str(paper_position['entry_price'])) == Decimal('50000.0')
    else:
        # Paper trading mode returns Decimal
        assert paper_position == Decimal('0')

    # Test position updates
    await trading_system.execute_order('buy', Decimal('0.5'), Decimal('51000.0'))
    updated_position = await trading_system.get_position("BTC-USD")
    if isinstance(updated_position, dict):
        assert Decimal(str(updated_position['size'])) == Decimal('1.5')
        # Verify weighted average price calculation
        expected_avg_price = (Decimal('1.0') * Decimal('50000.0') +
                            Decimal('0.5') * Decimal('51000.0')) / Decimal('1.5')
        assert Decimal(str(updated_position['entry_price'])) == expected_avg_price
    else:
        assert updated_position == Decimal('0')
```

Key testing considerations:
- Always convert position values to Decimal for comparisons
- Handle both dictionary and Decimal return formats
- Test weighted average price calculations with Decimal arithmetic
- Verify paper trading mode returns Decimal('0') for positions
- Include tests for position updates, reductions, and closures

### Market Data Tests

The `test_market_data.py` file in `tests/unit/` directory provides unit tests for the Market Data component.
These tests ensure proper functionality of:

- Price updates (handling real-time price changes)
- Order book updates (managing order book data)
- Trade history updates (tracking trade history)
- Data validation (ensuring data integrity)

Example test structure:

```python
@pytest.mark.asyncio
async def test_price_updates(market_data_system):
    # Test price update mechanism
    new_price = 45000.75
    updated_price = await market_data_system.update_price(new_price)
    assert updated_price == new_price
    # ... (rest of the test)
```

Ensure to run these tests to validate the core components' behavior and coverage.

## Performance Testing

Performance tests should use the performance thresholds fixture:

```python
def test_api_performance(performance_thresholds):
    start_time = time.time()
    # Perform operation
    duration = time.time() - start_time
    assert duration <= performance_thresholds['api_response_time']
```

## Coverage Requirements

- Minimum 85% code coverage required
- All API endpoints must have tests
- All error scenarios must be covered
- Performance benchmarks must be established

## Best Practices

1. Use appropriate test categories (unit, integration, e2e)
2. Implement proper mocks for external dependencies
3. Follow the test naming convention: `test_<functionality>_<scenario>`
4. Include both success and failure scenarios
5. Keep tests focused and maintainable
6. Use appropriate fixtures and utilities
7. Document complex test scenarios

## Example Test Implementation

```python
import pytest
from crypto_j_trader.tests.utils import (
    async_test,
    test_config,
    MockCoinbaseResponses
)

@pytest.mark.unit
@async_test
async def test_order_creation():
    # Arrange
    mock_response = MockCoinbaseResponses.create_order()
    
    # Act
    result = await create_test_order()
    
    # Assert
    assert result.order_id == mock_response['order_id']
    assert result.status == 'success'

@pytest.mark.integration
async def test_order_workflow(test_config):
    # Test complete order workflow
    pass

@pytest.mark.performance
def test_order_execution_time(performance_thresholds):
    # Test execution performance
    pass
```

## Continuous Integration

The test suite is integrated with CI/CD pipelines and runs:
- On every pull request
- Before deployment
- On scheduled intervals

## Getting Started

1. Install test dependencies:
```bash
pip install -r requirements-dev.txt
```

2. Run the test suite:
```bash
python scripts/run_tests.py
```

3. Review coverage reports in `coverage_html_report/`

For more details, review the test configuration in `pytest.ini` and available fixtures in `conftest.py`.