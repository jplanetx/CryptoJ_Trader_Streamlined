# Phase 5 - Part 2: Debugging WebSocket Handler Tests and Achieving Coverage

**Objective:** Debug failing WebSocket Handler tests, increase overall test coverage to 85%, and ensure stability of Market Data and Order Execution components.

**Context:**
- Current overall test coverage is 9%, with Risk Management (93%), Emergency Manager (100%), and Trading Core (37%) partially covered.
- Market Data and Order Execution unit tests are passing with estimated > 80% coverage each.
- WebSocket Handler unit tests in `test_websocket_handler.py` are failing with `AttributeError` and `AssertionError`.
- Phase 5 aims to achieve 85% system-wide test coverage and robust unit tests for all core components.

**Tasks:**

1. **Debug WebSocket Handler Unit Tests:**
    - **Identify Root Cause:** Analyze the test failures in `test_websocket_handler.py`. Focus on `AttributeError` and `AssertionError` to understand the specific issues.
    - **Error Reproduction:** Run the failing tests individually and in the suite to reproduce the errors consistently.
    - **Code Inspection:** Review the `WebSocketHandler` class in `crypto_j_trader/src/trading/websocket_handler.py` and the test file `crypto_j_trader/tests/unit/test_websocket_handler.py`. Pay close attention to:
        - Mocking and patching of `websockets` library.
        - Asynchronous test setup and teardown.
        - Assertion logic in test cases.
        - Configuration loading and usage within tests.
    - **Dependency Versions:** Verify compatibility of `websockets` and `pytest-asyncio` versions.
    - **Logging and Tracing:** Add detailed logging within the WebSocketHandler class and test functions to trace execution flow and variable states during test runs.
    - **Fix and Refactor:** Implement necessary code fixes and refactor test cases to resolve the `AttributeError` and `AssertionError`.

2. **Increase Test Coverage:**
    - **Target 85% Overall Coverage:** Expand unit tests to increase overall system coverage to at least 85%.
    - **Prioritize Trading Core:** Focus on increasing coverage for `crypto_j_trader/src/trading/trading_core.py`, which is currently at 37%.
    - **Coverage Gaps:** Identify uncovered code paths and branches in all modules using coverage reports.
    - **Implement New Tests:** Write new unit tests to cover uncovered code sections, focusing on:
        - Edge cases and error conditions.
        - Input validation and data sanitization.
        - Complex logic and algorithms within Trading Core and other modules.
    - **Review Existing Tests:** Refactor and improve existing tests for clarity, robustness, and coverage effectiveness.

3. **Run Full Test Suite and Generate Coverage Report:**
    - **Execute All Tests:** Run the complete unit test suite using `pytest`.
    - **Verify Test Pass Rates:** Ensure all unit tests for Market Data, Order Execution, and WebSocket Handler are passing.
    - **Generate Coverage Report:** Produce a detailed coverage report using `pytest-cov` to assess overall and module-specific coverage.
    - **Analyze Coverage Results:** Identify remaining coverage gaps and areas for further testing.

4. **Documentation and Handoff:**
    - **Update `Updates/update_log_20250202_0403.md`:** Add details on debugging WebSocket Handler tests, coverage improvements, and any remaining issues.
    - **Prepare for Phase 6:** Once 85% coverage is achieved and all unit tests are passing, prepare documentation and notes for transitioning to Phase 6.

**Example Test Cases and Guidance:**

### Debugging WebSocket Handler Tests
- **Test Case Example (Failing):**
  ```python
  async def test_websocket_connection_failure(mocker, ws_handler):
      mocker.patch('websockets.connect', side_effect=WebSocketException("Connection refused"))
      with pytest.raises(WebSocketException):
          await ws_handler.connect()
      assert not ws_handler.is_connected
  ```
  - **Debugging Steps:**
    1. Run this test case in isolation: `pytest crypto_j_trader/tests/unit/test_websocket_handler.py::test_websocket_connection_failure`
    2. Examine the error output to identify if it's an `AttributeError` or `AssertionError`.
    3. Check if the `mocker.patch` is correctly applied and if `WebSocketException` is correctly imported.
    4. Add logging in `ws_handler.connect()` to trace the connection attempt and exception handling.

### Increasing Trading Core Coverage
- **Focus Areas:** `trading_core.py` logic for order processing, strategy execution, and risk checks.
- **Test Example (Trading Core - Order Processing):**
  ```python
  async def test_process_market_order(trading_core, mock_exchange_service):
      order_params = {...} # Define market order parameters
      await trading_core.process_order(order_params)
      mock_exchange_service.execute_order.assert_called_once()
      # Add assertions to verify order status, position updates, etc.
  ```
  - **Guidance:**
    - Mock `ExchangeService` to isolate Trading Core logic.
    - Test different order types (market, limit, stop).
    - Verify order status updates and position tracking.
    - Cover error scenarios like insufficient balance, invalid symbols, etc.

**Expected Outcomes:**
- Resolved `AttributeError` and `AssertionError` in WebSocket Handler tests.
- Passing unit test suite for Market Data, Order Execution, and WebSocket Handler.
- Increased overall test coverage to 85% or higher.
- Improved stability and reliability of core trading components.
- Comprehensive coverage report and updated documentation for Phase 5 completion.

**Deliverables:**
- Updated `crypto_j_trader/src/trading/websocket_handler.py` with bug fixes and improvements.
- Updated `crypto_j_trader/tests/unit/test_websocket_handler.py` with passing test cases.
- New unit tests in `crypto_j_trader/tests/unit/` to increase coverage, especially for Trading Core.
- Updated coverage report (e.g., `coverage_html_report/index.html`).
- Updated `Updates/update_log_20250202_0403.md` with progress and results.
- `docs/next_thread_prompt_phase5_part2.md` for handoff to the next thread.
