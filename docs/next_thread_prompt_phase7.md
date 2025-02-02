# Next Thread Prompt: Phase 7 - Test Suite Debugging and Path Resolution

## Background

Phase 6 implemented comprehensive test suites for the Risk Management, Emergency Manager, Health Monitor, and WebSocket Handler components. However, all tests are currently failing, likely due to path resolution issues and potential import problems in the test structure.

## Current Status

### Test Implementation Status
- Risk Management tests: Implemented but failing
- Emergency Manager tests: Implemented but failing
- Health Monitor tests: Implemented but failing
- WebSocket Handler tests: Implemented but failing

### Files Requiring Review
```
/crypto_j_trader
    /src
        /trading
            risk_management.py
            emergency_manager.py
            health_monitor.py
            websocket_handler.py
    /tests
        /unit
            test_risk_management.py
            test_emergency_shutdown.py
            test_health_monitor.py
            test_websocket_handler.py
```

## Critical Issues to Address

1. **Path Resolution:**
   - Import paths in test files need to be corrected
   - Module resolution structure needs review
   - Python path configuration may need adjustment

2. **Test Infrastructure:**
   - pytest configuration needs verification
   - Test dependencies need to be confirmed
   - Test fixtures may need restructuring

3. **Module Dependencies:**
   - Cross-module dependencies need review
   - Mock implementations may need adjustment
   - Async test configurations need verification

## Development Priorities

1. **Test Infrastructure Setup**
   - Create proper conftest.py with shared fixtures
   - Setup correct import paths
   - Configure pytest for async testing

2. **Module Path Resolution**
   - Implement proper package structure
   - Create __init__.py files where needed
   - Set up proper import references

3. **Test Suite Debugging**
   - Debug and fix path resolution errors
   - Correct import statements
   - Verify mock implementations
   - Fix async test configurations

## Technical Requirements

### 1. Test Configuration Requirements
- Create proper conftest.py file
- Set up pytest-asyncio correctly
- Configure test paths appropriately
- Set up coverage reporting

### 2. Module Structure Requirements
- Verify package hierarchy
- Implement correct relative imports
- Set up proper module initialization

### 3. Testing Framework Requirements
- pytest
- pytest-asyncio
- pytest-mock
- pytest-cov

## Success Criteria

1. **All Tests Passing**
   - Fix path resolution issues
   - Correct import errors
   - Resolve mock configuration problems
   - Fix async test setup

2. **Coverage Requirements**
   - Maintain existing test coverage
   - Ensure all tests are discovered
   - Verify coverage reporting works

3. **Documentation**
   - Update test running instructions
   - Document test configuration
   - Provide troubleshooting guide

## Notes

- Focus on fixing infrastructure before debugging individual test failures
- Ensure async tests are properly configured
- Verify all dependencies are correctly installed
- Document any changes to test structure

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

1. Create proper test configuration:
   ```python
   # conftest.py example
   import pytest
   import sys
   import os

   # Add project root to Python path
   project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
   sys.path.insert(0, project_root)

   @pytest.fixture
   def mock_websocket():
       # Implement shared websocket mock
       pass
   ```

2. Verify import structure:
   ```python
   # Example correct import structure
   from crypto_j_trader.src.trading.risk_management import RiskManager
   from crypto_j_trader.src.trading.emergency_manager import EmergencyManager
   ```

3. Debug and fix test failures:
   ```bash
   # Commands to run with detailed output
   pytest -v --tb=long
   pytest -v --pdb  # For interactive debugging
   ```

## Questions for Next Implementation

1. Are all required dependencies installed and configured correctly?
2. Is the project structure set up properly for testing?
3. Are async tests configured correctly with pytest-asyncio?
4. Are mock objects and fixtures implemented correctly?

Please review and address these issues before proceeding with additional feature implementation.