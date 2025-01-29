# Codebase Cleanup Plan

## Core Trading System Requirements

### Essential Components
1. **Trading Core** (`trading_core.py`)
   - Basic order execution
   - Position management
   - Simple portfolio tracking

2. **Risk Management** (`risk_management.py`)
   - Basic position sizing
   - Stop loss handling
   - Simple risk limits

3. **WebSocket Handler** (`websocket_handler.py`)
   - Market data streaming
   - Basic error handling
   - Connection management

### Essential Tests
1. `test_trading_flow.py` - Core trading flow
2. `test_risk_management.py` - Basic risk controls
3. `test_websocket_handler.py` - Data streaming

## Components to Remove/Defer

### Remove Now
1. **Dynamic Weights System**
   - `test_dynamic_weights.py`
   - Complex weight calculations
   - Reason: Not essential for initial trading

2. **Portfolio Rebalancing**
   - `test_portfolio_rebalancing.py`
   - Complex rebalancing logic
   - Reason: Can start with simple position management

3. **Market Data Analysis**
   - `test_market_data.py`
   - Complex market analysis
   - Reason: Start with basic price data only

4. **Advanced Monitoring**
   - `test_monitor.py`
   - Complex monitoring systems
   - Reason: Use basic logging initially

### Defer for Later
1. **Portfolio Manager**
   - Advanced portfolio optimization
   - Complex allocation strategies
   - Add after basic trading is stable

2. **Emergency Shutdown**
   - Advanced shutdown procedures
   - Complex recovery mechanisms
   - Implement basic version only

## Simplified Project Structure

```
crypto_j_trader/
├── src/
│   ├── trading/
│   │   ├── trading_core.py      # Simplified trading logic
│   │   ├── risk_management.py   # Basic risk controls
│   │   └── websocket_handler.py # Market data streaming
│   └── utils/
│       └── monitoring.py        # Basic logging
├── tests/
│   ├── integration/
│   │   └── test_trading_flow.py # Core flow tests
│   └── unit/
│       ├── test_risk_management.py
│       └── test_websocket_handler.py
└── config/
    └── trading_config.json      # Simplified config
```

## Implementation Steps

### 1. Clean Up Phase
1. Create new branch 'minimal-viable-trader'
2. Remove non-essential components
3. Simplify existing core components
4. Update configuration structure

### 2. Core Implementation
1. Implement basic trading logic
   - Market order execution
   - Simple position tracking
   - Basic risk limits

2. Implement basic risk management
   - Fixed position sizing
   - Simple stop losses
   - Basic risk limits

3. Implement basic WebSocket handling
   - Price data streaming
   - Basic error handling
   - Simple reconnection logic

### 3. Testing Focus
1. Core trading flow
   - Order execution
   - Position management
   - Basic risk controls

2. Basic integration tests
   - End-to-end trading flow
   - Market data handling
   - Risk limit enforcement

## Timeline

### Week 1: Minimal Viable System
- Day 1: Cleanup and simplification
- Day 2: Core trading implementation
- Day 3: Basic testing and validation
- Day 4: Paper trading setup
- Day 5: Paper trading validation

### Week 2: Live Trading
- Day 1-2: Live configuration setup
- Day 3-4: Controlled live testing
- Day 5: Full live deployment

## Success Criteria
1. System can execute basic trades
2. Risk limits are enforced
3. Market data streams reliably
4. Position tracking is accurate
5. Basic logging is functional

## Future Enhancements
After successful live trading:
1. Add portfolio optimization
2. Implement advanced risk controls
3. Add sophisticated monitoring
4. Enhance emergency procedures

## Recommendation
Start fresh with the minimal viable system:
1. Create new branch from current code
2. Remove non-essential components
3. Focus on core trading functionality
4. Progress to live trading faster
5. Add complexity gradually after success

This approach will:
- Reduce complexity
- Speed up implementation
- Lower risk of issues
- Provide faster path to live trading
- Allow gradual enhancement