#!/usr/bin/env python
"""
Simplified test runner with better error handling
"""
import os
import sys
import subprocess
from pathlib import Path

def run_command(cmd, cwd=None, env=None):
    """Run a command and print output in real-time."""
    process = subprocess.Popen(
        cmd,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        bufsize=1
    )
    
    # Print output in real-time
    for line in process.stdout:
        print(line, end='')
    
    # Wait for the process to complete
    return_code = process.wait()
    
    # Print any errors
    error_output = process.stderr.read()
    if error_output:
        print("ERROR OUTPUT:", file=sys.stderr)
        print(error_output, file=sys.stderr)
        
    return return_code

def main():
    """Run tests with proper configuration."""
    project_root = Path(__file__).parent.parent
    
    # Set up environment
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project_root)
    
    print("Installing package in development mode...")
    install_result = run_command(
        [sys.executable, "-m", "pip", "install", "-e", "."],
        cwd=project_root,
        env=env
    )
    
    if install_result != 0:
        print("Failed to install package")
        return install_result
    
    print("\nRunning basic tests...")
    basic_result = run_command(
        [
            sys.executable, "-m", "pytest",
            "crypto_j_trader/tests/unit/test_basic.py",
            "-v",
            "--color=yes"
        ],
        cwd=project_root,
        env=env
    )
    
    if basic_result != 0:
        print("Basic tests failed. Fixing core functionality first.")
        return basic_result
    
    print("\nRunning full test suite...")
    full_result = run_command(
        [
            sys.executable, "-m", "pytest",
            "crypto_j_trader/tests",
            "-v",
            "--cov=crypto_j_trader",
            "--cov-report=term-missing",
            "--color=yes"
        ],
        cwd=project_root,
        env=env
    )
    
    return full_result

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nTest run interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nError running tests: {e}", file=sys.stderr)
        sys.exit(1)