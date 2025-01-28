# CryptoJ Trader

An automated cryptocurrency trading platform built in Python that integrates with Coinbase Advanced for executing trades. The system implements sophisticated trading strategies with risk management, portfolio optimization, and dynamic weight calculations.

## Features

- ✅ Real-time market data monitoring via WebSocket
- ✅ Risk management with position sizing and stop losses
- ✅ Portfolio optimization with dynamic weighting
- ✅ Support for paper trading and live trading modes
- ✅ Comprehensive test coverage
- ✅ CI/CD pipeline integration

## Project Structure

```
crypto_j_trader/
├── src/                    # Source code
│   ├── trading/           # Core trading logic
│   │   ├── trading_core.py    # Main trading functionality
│   │   ├── risk_management.py # Risk management system
│   │   └── websocket_handler.py # Real-time data handling
│   └── utils/             # Utility functions
│       └── monitoring.py      # System monitoring
├── tests/
│   ├── unit/             # Unit tests
│   └── integration/      # Integration tests
├── config/               # Configuration files
├── docs/                # Documentation
├── scripts/             # Utility scripts
└── vendor/              # Third-party dependencies
```

## Installation

1. Clone the repository:
```bash
git clone [repository-url]
cd crypto_j_trader
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Copy example configuration:
```bash
cp config.example.json config.json
cp .env.example .env
```

5. Configure API credentials:
- Create a Coinbase Advanced API key
- Add credentials to cdp_api_key.json

## Configuration

1. Main configuration (`config.json`):
```json
{
  "paper_trading": true,
  "trading_pairs": ["BTC-USD", "ETH-USD"],
  "default_interval": "5m",
  "max_candles": 100,
  "risk_per_trade": 0.02
}
```

2. Environment variables (`.env`):
```
LOG_LEVEL=INFO
PAPER_TRADING=true
```

## Usage

1. Start in paper trading mode:
```bash
python -m crypto_j_trader.src.main
```

2. Run tests:
```bash
pytest tests/
pytest tests/ --cov=crypto_j_trader
```

## Development

Please see [CONTRIBUTING.md](docs/CONTRIBUTING.md) for development guidelines, including:
- Code style and standards
- Branch strategy
- Testing requirements
- Pull request process

## Documentation

- [Project Overview & Architecture](docs/project_overview_and_architecture.md)
- [Deployment Guide](docs/deployment_guide.md)
- [CI/CD Pipeline](docs/ci_cd_explanation.md)

## Testing

The project includes:
- Unit tests for individual components
- Integration tests for end-to-end validation
- Performance benchmarks
- Paper trading validation suite

Run the test suite:
```bash
pytest tests/unit/           # Run unit tests
pytest tests/integration/    # Run integration tests
pytest --cov=crypto_j_trader # Check coverage
```

## Monitoring

The system provides:
- Real-time performance metrics
- Risk management alerts
- Trading activity logs
- System health monitoring

## Safety Features

- Emergency shutdown procedures
- Position size limits
- Daily loss limits
- API rate limiting protection
- Continuous system health monitoring

## License

[Your license here]

## Contact

For questions or support:
- GitHub Issues: [repository-url/issues]
- Documentation: [documentation-url]
