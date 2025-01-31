#!/usr/bin/env python
"""
Test runner script with coverage reporting and proper path setup
"""

import os
import sys
import pytest
import coverage

def main():
    """Run tests with coverage and generate reports."""
    # Add project root to Python path
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, project_root)
    
    # Exclude archived tests
    excluded_tests = [
        'crypto_j_trader/tests/archive/*',
    ]
    
    # Start coverage
    cov = coverage.Coverage()
    cov.start()

    # Run tests
    args = [
        "--verbose",
        "-v",
        "--color=yes",
        "--cov=crypto_j_trader",
        "--cov-report=term-missing",
        "--cov-report=html",
    ]
    
    # Add test directories but exclude archived tests
    args.extend([
        "crypto_j_trader/tests/unit/",
        "crypto_j_trader/tests/integration/",
    ])
    
    # Add any command line arguments
    args.extend(sys.argv[1:])
    
    result = pytest.main(args)

    # Stop coverage and generate reports
    cov.stop()
    cov.save()
    cov.report()
    
    return result

if __name__ == "__main__":
    sys.exit(main())