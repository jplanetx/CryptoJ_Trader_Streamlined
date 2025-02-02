# Next Thread Prompt: Phase 9 - Market Data Test Suite Debugging and Trading Core Tests

## Background

Phase 8 focused on debugging the test suite, specifically addressing issues in `test_emergency_manager.py` and starting to look at `test_market_data.py`. While `test_emergency_manager.py` unit tests are now passing, `test_market_data.py` and other test suites still have failing tests and errors.

The primary goal for Phase 9 is to continue debugging and resolving the remaining test failures, particularly in `test_market_data.py` and `test_trading_core_quick.py`.

## Current Status

### Test Implementation Status
- Risk Management tests: Passing
- Emergency Manager tests: Passing
- Health Monitor tests: Implemented but failing
- WebSocket Handler tests: Implemented but failing
- Market Data tests: Implemented but failing
- Trading Core tests: Implemented but failing

### Critical Issues to Address

1. **Market Data Test Suite Debugging:**
    - `test_market_data.py` has failing tests and errors related to fixture usage and mock implementations.
    - Need to resolve `AttributeError` and `fixture 'mocker' not found` errors in `test_market_data.py`.
    - Investigate `mock_exchange_service` fixture and `MockExchangeService` implementation for correctness and completeness.

2. **Trading Core Test Suite Debugging:**
    - `test_trading_core_quick.py` needs to be run and debugged.
    - Identify and fix any failing tests in `test_trading_core_quick.py`.

3. **Overall Test Infrastructure:**
    - Ensure pytest configuration is correct and efficient.
    - Verify pytest-asyncio setup for asynchronous tests.
    - Improve test fixture reusability and organization.

## Development Priorities

1. **Debug `test_market_data.py` Tests:**
    - Focus on resolving the remaining failures and errors in `test_market_data.py`.
    - Pay special attention to `test_real_time_price_updates_from_websocket` and `test_error_recovery` tests.
    - Ensure `mock_exchange_service` fixture and `MockExchangeService` are correctly implemented and used in tests.

2. **Debug `test_trading_core_quick.py` Tests:**
    - Run `test_trading_core_quick.py` test suite.
    - Debug and fix any failing tests in `test_trading_core_quick.py`.

3. **Improve Test Fixtures and Mocks:**
    - Review and enhance test fixtures, especially `mock_exchange_service`, to ensure they are robust and cover necessary test scenarios.
    - Improve mock implementations in `crypto_j_trader/tests/utils/mocks/coinbase_mocks.py` as needed.

## Technical Requirements

### 1. Test Debugging and Fixing
- Debug and fix failing tests in `crypto_j_trader/tests/unit/test_market_data.py`.
- Debug and fix failing tests in `crypto_j_trader/tests/unit/test_trading_core_quick.py`.

### 2. Test Infrastructure Improvement
- Review and improve test fixtures in `crypto_j_trader/tests/utils/fixtures/`.
- Enhance mock implementations in `crypto_j_trader/tests/utils/mocks/`.

### 3. Testing Framework Requirements
- pytest
- pytest-asyncio
- pytest-mock
- pytest-cov
- websockets
- psutil

## Success Criteria

1. **Passing Market Data Tests:**
    - All unit tests in `crypto_j_trader/tests/unit/test_market_data.py` should pass without errors or failures.

2. **Passing Trading Core Tests:**
    - All unit tests in `crypto_j_trader/tests/unit/test_trading_core_quick.py` should pass without errors or failures.

3. **Improved Test Infrastructure:**
    - Test fixtures and mock implementations should be reviewed and improved for better reusability and maintainability.

## Notes

- Continue systematic debugging and incremental fixes.
- Use pytest verbose output and traceback options for detailed debugging.
- Ensure all dependencies are installed and up to date.
- Document all changes made to test infrastructure and code.

## Dependencies

### Required Packages
```toml
[test]
pytest = ">=7.0.0"
pytest-asyncio = ">=0.18.0"
pytest-cov = ">=3.0.0"
pytest-mock = ">=3.10.0"
websockets = ">=10.0"
psutil = ">=5.8.0"
```

### System Requirements
- Python 3.11+
- pip/poetry for dependency management
- pytest and plugins installed
- Development tools configured

## Next Steps

1. **Debug `test_market_data.py` Tests:**
    - Run `python -m pytest crypto_j_trader/tests/unit/test_market_data.py -v` to examine test outputs and errors.
    - Investigate `mock_exchange_service` fixture and `MockExchangeService` in `coinbase_mocks.py`.
    - Fix fixture and mock implementations as needed.

2. **Debug `test_trading_core_quick.py` Tests:**
    - Run `python -m pytest crypto_j_trader/tests/unit/test_trading_core_quick.py -v` to examine test outputs and errors.
    - Analyze failing tests and identify root causes.
    - Fix code or test configurations to resolve errors.

Please review and address these issues to ensure a stable and reliable testing environment for further development and to proceed towards paper trading and live launch.