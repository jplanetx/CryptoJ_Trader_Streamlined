# Thread Initialization Guide

## Core Files to Share

### 1. Project Requirements
- `/docs/product/prd.md`: Core product requirements and objectives
- `/docs/product/success_metrics.md`: Performance targets (40% annual return, risk limits)
- `/docs/product/user_personas.md`: Single-user focus and requirements

### 2. Architecture & Design
- `/docs/architectural_decisions.md`: System architecture and design decisions
- `/docs/technical/backend/trading_engine.md`: Trading engine specifications
- `/docs/flows/trading_flows.md`: Trading operation workflows
- `/docs/flows/risk_management.md`: Risk management procedures

### 3. Configuration
- `/config/config.example.json`: Configuration structure
- `/crypto_j_trader/paper_config.json`: Paper trading settings
- `/docs/configuration_management.md`: Configuration management guide

### 4. Core Implementation Files
- `/crypto_j_trader/src/trading/trading_core.py`: Main trading logic
- `/crypto_j_trader/src/trading/paper_trading.py`: Paper trading implementation
- `/crypto_j_trader/src/trading/risk_management.py`: Risk management system

## Technical Details to Include

### 1. Version Information
```yaml
python_version: ">=3.8"
framework_versions:
  pytest: ">=7.0.0"
  pytest-asyncio: ">=0.25.0"
  pytest-cov: ">=3.0.0"
```

### 2. Project Structure
```
crypto_j_trader/
├── src/
│   ├── trading/        # Core trading components
│   ├── risk_management/# Risk management systems
│   └── market_data/    # Market data handling
├── tests/
│   ├── unit/          # Unit tests
│   └── integration/   # Integration tests
└── config/            # Configuration files
```

### 3. Critical Parameters
```json
{
  "performance_targets": {
    "annual_return_target": 40,
    "minimum_return": 20,
    "max_drawdown": 15
  },
  "risk_limits": {
    "position_size": 2,
    "daily_drawdown": 5
  }
}
```

## Thread Context Requirements

### 1. Current Development Phase
```yaml
phase: "paper_trading"
status: "implementation"
focus:
  - Trading execution validation
  - Risk management verification
  - Performance monitoring
  - Emergency procedures testing
```

### 2. Active Components
- Paper trading system
- Risk management controls
- Position tracking
- Performance monitoring
- Emergency procedures

### 3. Testing Requirements
- Unit test coverage >80%
- Integration tests passing
- Paper trading validation
- Risk control verification

## Documentation Standards

### 1. Code Documentation
```python
"""
Function/class documentation template:

Parameters:
    param1 (type): description
    param2 (type): description

Returns:
    type: description

Raises:
    ExceptionType: condition
"""
```

### 2. Configuration Documentation
```yaml
configuration:
  format: "JSON"
  validation: "required"
  fields:
    - name: field_name
      type: data_type
      description: "Field purpose"
```

### 3. Test Documentation
```python
"""
Test documentation template:

Test purpose:
1. What is being tested
2. Expected behavior
3. Success criteria

Setup requirements:
1. Required configurations
2. Test data
3. Environment setup
"""
```

## Environment Setup

### 1. Development Environment
```bash
# Environment setup
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Configuration
cp config/config.example.json config/config.json
cp .env.template .env
```

### 2. Testing Environment
```bash
# Test setup
pytest tests/unit/
pytest tests/integration/
```

## Version Control Guidelines

### 1. Branch Strategy
```yaml
branches:
  main: "Production-ready code"
  development: "Integration testing"
  feature: "prefix/feature-name"
```

### 2. Commit Standards
```yaml
commit_format: "type(scope): description"
types:
  - feat: "New features"
  - fix: "Bug fixes"
  - test: "Test additions/modifications"
  - docs: "Documentation updates"
```

## Success Criteria Reminder

1. Performance Targets:
   - 40% annual return target
   - 20% minimum acceptable return
   - 15% maximum drawdown limit

2. Risk Controls:
   - 2% maximum position size
   - 5% daily drawdown limit
   - Real-time risk monitoring

3. System Requirements:
   - 99.9% uptime
   - <100ms order execution
   - Real-time position tracking

This guide should be shared at the start of each development thread to ensure consistency and maintain focus on the core objectives.
