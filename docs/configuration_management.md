# Configuration Management Guide

## Overview

This guide explains how to manage configurations securely in the CryptoJ Trading System. The system uses a layered configuration approach to handle different environments (development, production, test) while ensuring sensitive data remains secure.

## Configuration Structure

```
config/
├── config.example.json     # Template with documentation
├── config.json            # Local development config (gitignored)
├── production.json        # Production settings (gitignored)
├── test_config.json      # Test configuration
├── cdp_api_key.json      # API credentials (gitignored)
└── settings.py           # Configuration management module
```

## Setting Up Local Environment

1. Run the initialization script:
```bash
python scripts/init_config.py
```

This will:
- Create necessary configuration files from templates
- Set up empty credential files
- Initialize development environment settings

2. Update your API credentials:
   - Edit `config/cdp_api_key.json` with your Coinbase Advanced Trade API credentials
   - Never commit this file to version control

3. Configure environment settings:
   - Copy `.env.template` to `.env`
   - Update environment variables as needed

## Configuration Types

### 1. Environment Configuration

The system supports three environments:
- Development (default)
- Production
- Test

Set the environment using the `ENVIRONMENT` environment variable:
```bash
export ENVIRONMENT=development  # or production, test
```

### 2. Trading Configuration

Main configuration file (`config.json`) includes:
- Trading pairs and weights
- Risk management settings
- WebSocket configurations
- System health parameters

Example:
```json
{
  "trading_pairs": [
    {
      "pair": "BTC-USD",
      "weight": 0.6,
      "precision": 8
    }
  ],
  "risk_management": {
    "daily_loss_limit": 0.02,
    "position_size_limit": 0.1
  }
}
```

### 3. Emergency Management

Emergency configuration includes:
- Position limits
- Risk thresholds
- Emergency shutdown parameters

### 4. API Credentials

API credentials are stored separately in `cdp_api_key.json`:
```json
{
  "api_key": "your_api_key",
  "api_secret": "your_api_secret",
  "paper_trading": true
}
```

## Making Configuration Changes

1. Create a GitHub issue using the Configuration Change template
2. Make changes in your local environment first
3. Test thoroughly
4. Update documentation if needed
5. For production changes:
   - Create a pull request
   - Include test results
   - Get team review
   - Update monitoring if needed

## Security Best Practices

1. Never commit sensitive data:
   - API keys
   - Production configurations
   - Private keys
   - Credentials

2. Use environment variables for sensitive values:
   - Use `.env` file locally
   - Use secure environment variable storage in production

3. Regular security checks:
   - Audit gitignored files
   - Rotate API keys periodically
   - Review access permissions

4. Backup Management:
   - Keep secure backups of production configurations
   - Document recovery procedures
   - Test restoration process

## Validation

Configuration validation happens at multiple levels:

1. File-level validation:
   - JSON syntax
   - Required fields
   - Data types

2. Environment-specific validation:
   - Production requires stricter settings
   - Test environment enforces paper trading
   - Development allows flexible settings

3. Runtime validation:
   - Trading pair existence
   - Position limits
   - Risk parameters

## Monitoring

Monitor configuration-related issues:
1. Watch for configuration load errors
2. Track validation failures
3. Monitor emergency shutdowns
4. Log configuration changes

## Development Workflow

1. Use `config.example.json` as a template
2. Make changes in development first
3. Test thoroughly with `test_config.json`
4. Review changes with team
5. Deploy to production

## Troubleshooting

Common issues and solutions:

1. Missing Configuration:
   - Run `python scripts/init_config.py`
   - Check file permissions

2. Validation Errors:
   - Verify JSON syntax
   - Check required fields
   - Validate data types

3. Environment Issues:
   - Verify `ENVIRONMENT` setting
   - Check `.env` file
   - Validate credentials

## Additional Resources

- [Coinbase Advanced Trade API Documentation](https://docs.cdp.coinbase.com/advanced-trade/docs/welcome)
- [Project Architecture Documentation](./architectural_decisions.md)
- [Deployment Guide](./deployment_guide.md)