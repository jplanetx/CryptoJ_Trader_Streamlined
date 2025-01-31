#!/usr/bin/env python
"""
Test runner script with coverage reporting
"""

import os
import sys
import pytest
import coverage

def main():
    """Run tests with coverage and generate reports."""
    # Start coverage
    cov = coverage.Coverage()
    cov.start()

    # Run tests
    args = [
        "--verbose",
        "--asyncio-mode=strict",
        "-v",
        "--color=yes",
        "--cov=crypto_j_trader",
        "--cov-report=term-missing",
        "--cov-report=html",
        "crypto_j_trader/tests/"
    ]
    
    # Add any command line arguments
    args.extend(sys.argv[1:])
    
    result = pytest.main(args)

    # Stop coverage and generate reports
    cov.stop()
    cov.save()
    cov.report()
    
    # Generate HTML report
    cov.html_report()

    return result

if __name__ == "__main__":
    sys.exit(main())