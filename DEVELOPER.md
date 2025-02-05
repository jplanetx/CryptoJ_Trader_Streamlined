# CryptoJ Trader Developer Guide

## Getting Started

### Prerequisites
- Python 3.8 or higher
- pip package manager
- Git

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd crypto-j-trader
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Unix/MacOS
source venv/bin/activate
```

3. Install dependencies:
```bash
# For development
pip install -r requirements-dev.txt
# For production
pip install -r requirements.txt
```

## Configuration

### Environment Setup

1. Copy the environment template:
```bash
cp .env.template .env
```

2. Create your configuration file:
```bash
cp config/config.example.json config/config.json
```

### Configuration Options

The main configuration file (`config/config.json`) includes:

```json
{
  "coinbase_api_key": "your_api_key",
  "coinbase_api_secret": "your_api_secret",
  "trading_pairs": [
    {
      "pair": "BTC-USD",
      "weight": 0.6,
      "precision": 8
    },
    {
      "pair": "ETH-USD",
      "weight": 0.4,
      "precision": 6
    }
  ],
  "default_interval": "5m",
  "max_candles": 100,
  "log_level": "INFO",
  "paper_trading": true,
  "max_trade_size": 100,
  "min_trade_size": 10,
  "risk_per_trade": 0.02
}
```

Key configuration sections:

1. **API Configuration**
   - `coinbase_api_key`: Your Coinbase API key
   - `coinbase_api_secret`: Your Coinbase API secret

2. **Trading Parameters**
   - `trading_pairs`: List of trading pairs with weights and precision
   - `default_interval`: Default trading interval
   - `max_candles`: Maximum number of candlesticks to store
   - `paper_trading`: Enable/disable paper trading mode

3. **Risk Management**
   - `risk_per_trade`: Maximum risk per trade (as decimal)
   - `max_trade_size`: Maximum trade size allowed
   - `min_trade_size`: Minimum trade size allowed

4. **WebSocket Settings**
   - `websocket.enabled`: Enable/disable WebSocket connection
   - `websocket.reconnect_max_attempts`: Maximum reconnection attempts
   - `websocket.heartbeat_interval_seconds`: Heartbeat interval

## Testing

### Test Structure

The testing infrastructure is organized into:

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

### Running Tests

Use the test runner script:

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

### Test Categories

1. **Unit Tests**
   - Test individual components in isolation
   - Located in `tests/unit/`
   - Use `@pytest.mark.unit` decorator

2. **Integration Tests**
   - Test component interactions
   - Located in `tests/integration/`
   - Use `@pytest.mark.integration` decorator

3. **End-to-End Tests**
   - Test complete system workflows
   - Located in `tests/e2e/`
   - Use `@pytest.mark.e2e` decorator

### Writing Tests

Example test structure:

```python
import pytest
from crypto_j_trader.tests.utils import async_test, test_config

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
```

### Coverage Requirements

- Minimum 85% code coverage required
- All API endpoints must have tests
- All error scenarios must be covered
- Performance benchmarks must be established

## Development Workflow

1. Create a new branch for your feature/fix
2. Write tests for new functionality
3. Implement your changes
4. Ensure all tests pass
5. Submit a pull request

### Code Style

- Follow PEP 8 guidelines
- Use type hints
- Write docstrings for all functions and classes
- Keep functions focused and maintainable

### Best Practices

1. Write tests before implementing features
2. Document complex logic and decisions
3. Use appropriate error handling
4. Keep components loosely coupled
5. Follow the project's architectural patterns

## Troubleshooting

Common issues and solutions:

1. **API Connection Issues**
   - Verify API keys in configuration
   - Check network connectivity
   - Ensure proper WebSocket settings

2. **Test Failures**
   - Check mock data accuracy
   - Verify test environment setup
   - Review test logs in detail

## Additional Resources

- Project Architecture: See `docs/architectural_decisions.md`
- Deployment Guide: See `docs/deployment_guide.md`
- Contributing Guidelines: See `docs/CONTRIBUTING.md`