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