# Completion Threads for Steps 3.1 and 3.2

## Thread Overview
Based on the review findings, the following parallel threads need to be completed before moving to paper trading (Step 4).

### Thread 1: Core Order Execution
```
Role: You are Roo, a trading systems developer focused on core functionality.

Task:
1. Implement basic order execution in order_execution.py
2. Add position tracking
3. Fix failing unit tests
4. Verify integration tests

Focus Areas:
- order_execution.py (currently 21.05% coverage)
- Position tracking implementation
- Order execution test fixes
- Integration test completion

Success Criteria:
- All order_execution.py tests passing
- Position tracking functional
- Coverage above 80% for modified files
```

### Thread 2: Market Data Handler
```
Role: You are Roo, a market data systems expert focused on reliable data streaming.

Task:
1. Complete WebSocket handler implementation
2. Add proper error handling
3. Fix failing market data tests
4. Implement basic health checks

Focus Areas:
- market_data.py (currently 16.67% coverage)
- websocket_handler.py (currently 15.79% coverage)
- WebSocket reconnection logic
- Data validation

Success Criteria:
- Reliable market data streaming
- Proper error recovery
- Health check implementation
- Coverage above 80% for modified files
```

### Thread 3: Trading Core Enhancement
```
Role: You are Roo, a trading systems architect focused on core trading functionality.

Task:
1. Implement missing trading core methods
2. Add health monitoring
3. Fix failing core tests
4. Complete integration scenarios

Focus Areas:
- trading_core.py (currently 23.08% coverage)
- Core trading logic
- System health monitoring
- Integration test scenarios

Success Criteria:
- All trading core tests passing
- Health monitoring functional
- Integration tests complete
- Coverage above 80% for modified files
```

### Thread 4: Risk Management
```
Role: You are Roo, a risk management expert focused on trading safety.

Task:
1. Implement basic risk controls
2. Add position limits
3. Fix risk management tests
4. Add emergency shutdown tests

Focus Areas:
- risk_management.py (current coverage low)
- Position limit implementation
- Stop loss functionality
- Emergency procedures

Success Criteria:
- All risk controls functional
- Position limits enforced
- Emergency shutdown tested
- Coverage above 80% for modified files
```

## Execution Plan

### Order of Operations
1. Start Threads 1 and 2 in parallel
   - Core order execution and market data are foundational
   - Can be developed independently

2. Begin Thread 3 after Thread 1 reaches 50% completion
   - Trading core depends on order execution
   - Can start once basic order functionality is working

3. Begin Thread 4 after Thread 3 reaches 50% completion
   - Risk management builds on core trading
   - Requires working order execution and trading core

### Coordination Points
- Daily sync between Thread 1 and 2 teams
- Integration test coordination at 50% milestones
- Combined system testing when all threads reach 80% completion

### Moving to Paper Trading
Requirements before starting Step 4:
1. All critical tests passing
2. Coverage above 80% for core components
3. Basic health monitoring functional
4. Risk controls implemented and tested
5. Integration tests verifying full trading flow

## Thread Creation Commands

To start each thread, use these commands in separate terminals:

```bash
# Thread 1: Core Order Execution
new_task code "Implement core order execution following the prompt in docs/completion_threads_3.1_3.2.md Thread 1"

# Thread 2: Market Data Handler
new_task code "Implement market data handler following the prompt in docs/completion_threads_3.1_3.2.md Thread 2"

# Thread 3: Trading Core Enhancement
new_task code "Enhance trading core following the prompt in docs/completion_threads_3.1_3.2.md Thread 3"

# Thread 4: Risk Management
new_task code "Implement risk management following the prompt in docs/completion_threads_3.1_3.2.md Thread 4"