# Test Execution Guide

## Prerequisites

1. Environment Setup
```bash
# Open PowerShell as Administrator and navigate to project root
cd C:\Projects\CryptoJ_Trader_PT

# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install required packages
pip install pytest
pip install pytest-asyncio
pip install pytest-cov
```

2. Verify Project Structure
```
C:\Projects\CryptoJ_Trader_PT\
├── src/
│   └── trading/
│       ├── risk_management.py
│       ├── emergency_manager.py
│       ├── order_execution.py
│       ├── health_monitor.py
│       └── websocket_handler.py
├── tests/
│   ├── unit/
│   │   ├── test_risk_management.py
│   │   ├── test_emergency_shutdown.py
│   │   ├── test_order_execution.py
│   │   ├── test_health_monitor.py
│   │   └── test_websocket_handler.py
│   └── integration/
│       ├── test_trading_core.py
│       ├── test_trading_flow.py
│       └── test_trading_system.py
```

## Running Tests

### 1. Run All Tests
```bash
# From project root
pytest tests/ -v --cov=src

# With detailed output
pytest tests/ -v --cov=src --cov-report=term-missing
```

### 2. Run Specific Test Files
```bash
# Run risk management tests
pytest tests/unit/test_risk_management.py -v

# Run emergency shutdown tests
pytest tests/unit/test_emergency_shutdown.py -v

# Run integration tests
pytest tests/integration/ -v
```

### 3. Run Tests by Mark
```bash
# Run only unit tests
pytest -v -m unit

# Run only integration tests
pytest -v -m integration

# Run only critical tests
pytest -v -m critical
```

### 4. Debug Failed Tests
```bash
# Run with detailed traceback
pytest -v --tb=long

# Run with print statement output
pytest -v -s

# Run specific failed test
pytest tests/unit/test_risk_management.py::test_assess_risk_high_exposure -v
```

## Manual Testing Steps

1. Risk Management Testing
```python
# In Python interactive shell
from src.trading.risk_management import RiskManager

# Create instance
risk_manager = RiskManager(config={'max_position_size': 1.0})

# Test risk assessment
result = await risk_manager.assess_risk({'position_size': 0.5})
print(result)
```

2. Emergency Manager Testing
```python
# Test emergency mode
from src.trading.emergency_manager import EmergencyManager

manager = EmergencyManager()
await manager.validate_new_position('BTC-USD', 0.1, 50000)
```

3. WebSocket Testing
```python
# Test connection
from src.trading.websocket_handler import WebSocketHandler

handler = WebSocketHandler()
await handler.connect()
await handler.subscribe('BTC-USD')
```

## Common Issues and Solutions

1. Import Errors
- Ensure PYTHONPATH includes project root
- Verify virtual environment is activated
- Check file paths in imports

2. Async Test Failures
- Use pytest-asyncio markers
- Ensure proper cleanup in fixtures
- Check for unhandled coroutines

3. Mock Issues
- Verify mock return values
- Check mock call counts
- Ensure proper cleanup

4. Coverage Issues
- Run with --cov-report=html for detailed report
- Check uncovered lines in report
- Add tests for edge cases

## CI/CD Integration

1. GitHub Actions Workflow
```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      - name: Run tests
        run: |
          pytest tests/ -v --cov=src
```

## Monitoring Test Results

1. Generate Reports
```bash
# Generate HTML coverage report
pytest --cov=src --cov-report=html

# Generate XML report for CI
pytest --cov=src --cov-report=xml
```

2. Review Test Logs
```bash
# Save test output to file
pytest tests/ -v > test_results.log
```

Need help with any specific test or section?