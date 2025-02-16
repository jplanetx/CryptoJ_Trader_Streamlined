# AI Trading Prompts

## Overview
This document defines standardized prompts for AI interactions in the CryptoJ Trading system, focusing on achieving the target 40% annual return while maintaining strict risk management controls.

## Performance Tracking Prompts

### 1. Return Progress Analysis
```yaml
prompt_template:
  purpose: "Track progress toward annual return targets"
  format: |
    Analyze trading performance:
    - Current annual return: {current_return}
    - Target annual return: 40%
    - Minimum required: 20%
    - Days remaining: {days_remaining}
    - Current drawdown: {drawdown}
    
    Evaluate:
    1. Progress toward target (%)
    2. Required daily/weekly returns
    3. Risk adjustment needs
    4. Strategy effectiveness
    
    Provide analysis with:
    - Performance assessment
    - Risk recommendations
    - Strategy adjustments
    - Action items
```

### 2. Risk Compliance Check
```yaml
prompt_template:
  purpose: "Verify risk management compliance"
  format: |
    Check risk parameters:
    - Position sizes (<2% per trade)
    - Portfolio drawdown (<15% max)
    - Daily drawdown (<5% max)
    - Current exposure: {exposure}
    
    Verify:
    1. Position size compliance
    2. Drawdown limits
    3. Risk distribution
    4. Emergency triggers
    
    Provide assessment with:
    - Compliance status
    - Violation alerts
    - Required adjustments
    - Risk recommendations
```

## Trade Analysis Prompts

### 1. Pre-Trade Validation
```yaml
prompt_template:
  purpose: "Risk assessment for new trade"
  format: |
    Analyze trade risk for:
    - Order type: {order_type}
    - Trading pair: {pair}
    - Position size: {size}
    - Portfolio impact: {impact}
    
    Verify compliance:
    1. Position size (<2% of portfolio)
    2. Current drawdown status
    3. Market conditions
    4. Return contribution potential
    
    Provide risk assessment with:
    - Risk level (1-5)
    - Compliance status
    - Expected contribution to annual target
    - Go/No-go decision
```

### 2. Position Monitoring
```yaml
prompt_template:
  purpose: "Active position risk monitoring"
  format: |
    Evaluate position risk for:
    - Position ID: {position_id}
    - Entry price: {entry_price}
    - Current price: {current_price}
    - P&L: {pnl}
    - Contribution to annual return: {return_contribution}
    
    Assess:
    1. Performance impact
    2. Risk limit compliance
    3. Return target alignment
    4. Exit conditions
    
    Provide analysis with:
    - Risk status
    - Performance metrics
    - Target progress impact
    - Hold/Exit recommendation
```

## Strategy Optimization Prompts

### 1. Performance Optimization
```yaml
prompt_template:
  purpose: "Strategy optimization for return targets"
  format: |
    Analyze strategy performance:
    - Current annual return: {return_rate}
    - Win rate: {win_rate}
    - Average profit per trade: {avg_profit}
    - Risk-adjusted return: {sharpe_ratio}
    
    Evaluate:
    1. Progress toward 40% target
    2. Risk efficiency
    3. Implementation effectiveness
    4. Optimization opportunities
    
    Provide recommendations for:
    - Strategy adjustments
    - Risk optimization
    - Return enhancement
    - Implementation improvements
```

### 2. Risk Adjustment
```yaml
prompt_template:
  purpose: "Risk parameter optimization"
  format: |
    Analyze risk settings:
    - Current position sizes
    - Drawdown levels
    - Return volatility
    - Risk metrics
    
    Evaluate:
    1. Risk efficiency
    2. Return impact
    3. Safety margins
    4. Adjustment needs
    
    Provide recommendations for:
    - Position sizing
    - Risk limits
    - Safety parameters
    - Implementation changes
```

## Emergency Response Prompts

### 1. Market Event Response
```yaml
prompt_template:
  purpose: "Emergency market event analysis"
  format: |
    Analyze market emergency:
    - Event type: {event_type}
    - Impact on returns: {return_impact}
    - Affected positions: {positions}
    - Risk limit status: {risk_status}
    
    Evaluate:
    1. Return target impact
    2. Risk limit breaches
    3. Required actions
    4. Recovery steps
    
    Provide response plan:
    - Immediate actions
    - Position adjustments
    - Risk mitigation
    - Recovery process
```

### 2. System Event Response
```yaml
prompt_template:
  purpose: "System emergency analysis"
  format: |
    Analyze system emergency:
    - Issue type: {issue_type}
    - Trading impact: {trading_impact}
    - Risk status: {risk_status}
    - System state: {system_state}
    
    Assess:
    1. Performance impact
    2. Risk compliance
    3. Data integrity
    4. Recovery needs
    
    Provide response with:
    - Critical actions
    - Risk controls
    - Recovery steps
    - Validation checks
```

## Validation Requirements

### 1. Performance Validation
- Return calculation accuracy
- Risk limit compliance
- Position size verification
- Target progress tracking

### 2. Risk Validation
- Position size limits (<2%)
- Portfolio drawdown (<15%)
- Daily drawdown (<5%)
- Emergency trigger monitoring

## Usage Guidelines

### 1. Return Target Focus
- Track progress to 40% annual return
- Monitor minimum 20% threshold
- Assess risk-adjusted returns
- Verify strategy effectiveness

### 2. Risk Management
- Enforce position size limits
- Monitor drawdown thresholds
- Maintain risk balance
- Ensure emergency readiness

## Safety Requirements

### 1. Risk Controls
- Strict position size limits (2%)
- Maximum drawdown monitoring
- Return target alignment
- Emergency procedures

### 2. Validation Rules
- Performance verification
- Risk compliance checks
- Strategy effectiveness
- System safety monitoring
