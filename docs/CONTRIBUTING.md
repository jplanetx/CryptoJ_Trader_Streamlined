# Contributing to CryptoJ Trader

## Development Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements-dev.txt
```

3. Install local package in development mode:
```bash
pip install -e .
```

## Project Structure

```
crypto_j_trader/
├── src/                    # Source code
│   ├── trading/           # Core trading logic
│   └── utils/             # Utility functions
├── tests/
│   ├── unit/             # Unit tests
│   └── integration/      # Integration tests
├── config/               # Configuration files
├── docs/                # Documentation
├── scripts/             # Utility scripts
└── vendor/              # Third-party dependencies
```

## Branch Strategy

- `main` - Production-ready code
- `develop` - Development branch for integration
- `feature/*` - Feature branches
- `bugfix/*` - Bug fix branches
- `release/*` - Release preparation branches

### Branch Protection Rules
- Direct pushes to `main` are not allowed
- Pull requests require code review
- All status checks must pass before merging

## Development Guidelines

1. **Code Style**
   - Follow PEP 8 guidelines
   - Use type hints for function arguments and return types
   - Include docstrings for all public functions and classes

2. **Testing**
   - Write unit tests for new features
   - Maintain or improve test coverage
   - Run tests locally before pushing:
     ```bash
     python -m pytest tests/
     python -m pytest tests/ --cov=crypto_j_trader
     ```

3. **Git Workflow**
   - Create feature branches from `develop`
   - Keep commits focused and atomic
   - Write clear commit messages
   - Rebase feature branches on `develop`
   - Squash commits before merging

4. **Pull Requests**
   - Include clear description of changes
   - Reference related issues
   - Update documentation as needed
   - Add tests for new features
   - Keep PRs focused and reasonable in size

5. **Documentation**
   - Update README.md for user-facing changes
   - Document new features in appropriate docs
   - Keep API documentation current
   - Include usage examples for new features

## Paper Trading Testing

1. Always test new features in paper trading mode first
2. Verify risk management functionality
3. Test with various market conditions
4. Monitor system resource usage
5. Validate logging and monitoring

## Emergency Procedures

1. **Emergency Shutdown**
   - System can be stopped with Ctrl+C
   - Emergency shutdown closes all positions
   - Logs detail shutdown process

2. **Critical Issues**
   - Create issue with [CRITICAL] prefix
   - Notify project maintainers immediately
   - Document steps to reproduce
   - Include relevant logs and system state

## Performance Considerations

1. **Resource Usage**
   - Monitor memory usage
   - Profile CPU-intensive operations
   - Consider API rate limits
   - Optimize database queries

2. **Scalability**
   - Design for multiple trading pairs
   - Consider concurrent operations
   - Implement proper error handling
   - Use connection pooling

## Getting Help

- Review existing documentation
- Check closed issues for similar problems
- Ask questions in pull requests
- Contact project maintainers

Remember to always prioritize system stability and risk management when making changes.