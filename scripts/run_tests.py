#!/usr/bin/env python
"""
Test runner script for CryptoJ Trader with various configurations.
"""
import argparse
import subprocess
import sys
from typing import List

def run_tests(test_type: str = None, verbose: bool = False, coverage: bool = True) -> int:
    """Run tests with specified configuration.
    
    Args:
        test_type: Type of tests to run ('unit', 'integration', 'e2e', 'performance', or None for all)
        verbose: Whether to show verbose output
        coverage: Whether to generate coverage reports
    
    Returns:
        Exit code from pytest
    """
    cmd: List[str] = ["pytest"]
    
    # Add markers based on test type
    if test_type:
        if test_type not in ['unit', 'integration', 'e2e', 'performance', 'all']:
            print(f"Invalid test type: {test_type}")
            return 1
        if test_type != 'all':
            cmd.append(f"-m {test_type}")
    
    # Add verbosity
    if verbose:
        cmd.append("-vv")
    
    # Add coverage options
    if coverage:
        cmd.extend([
            "--cov=crypto_j_trader",
            "--cov-report=term-missing",
            "--cov-report=html:coverage_html_report",
            "--cov-report=xml:coverage.xml"
        ])
    
    # Run tests
    try:
        result = subprocess.run(" ".join(cmd), shell=True)
        return result.returncode
    except subprocess.CalledProcessError as e:
        print(f"Error running tests: {e}")
        return 1

def main() -> int:
    """Main entry point for test runner."""
    parser = argparse.ArgumentParser(description="Run CryptoJ Trader tests")
    
    parser.add_argument(
        "--type",
        choices=['unit', 'integration', 'e2e', 'performance', 'all'],
        default='all',
        help="Type of tests to run"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show verbose output"
    )
    
    parser.add_argument(
        "--no-coverage",
        action="store_true",
        help="Disable coverage reporting"
    )
    
    args = parser.parse_args()
    
    print(f"Running {args.type} tests...")
    return run_tests(
        test_type=args.type if args.type != 'all' else None,
        verbose=args.verbose,
        coverage=not args.no_coverage
    )

if __name__ == "__main__":
    sys.exit(main())