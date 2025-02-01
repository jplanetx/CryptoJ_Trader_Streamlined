@echo off
setlocal enabledelayedexpansion

:: Test Runner for CryptoJ Trader
set PYTHONPATH=%~dp0
set PYTEST_ADDOPTS=--no-cov-on-fail

:: Parse command line arguments
set FOCUS=
set COVERAGE_TARGET=80.0
set PARALLEL=

:parse_args
if "%~1"=="" goto :main
if /i "%~1"=="--emergency" (
    set FOCUS=emergency
    shift
    goto :parse_args
)
if /i "%~1"=="--integration" (
    set FOCUS=integration
    shift
    goto :parse_args
)
if /i "%~1"=="--performance" (
    set FOCUS=performance
    shift
    goto :parse_args
)
if /i "%~1"=="--coverage" (
    set COVERAGE_TARGET=%~2
    shift
    shift
    goto :parse_args
)
if /i "%~1"=="--parallel" (
    set PARALLEL=--parallel
    shift
    goto :parse_args
)
shift
goto :parse_args

:main
echo Running CryptoJ Trader Tests
echo ===========================
echo.

:: Run the test suite with pytest directly for emergency tests
if "%FOCUS%"=="emergency" (
    pytest -v --tb=short --strict-markers -p no:warnings --cov=crypto_j_trader --cov-report=term-missing --cov-report=xml --cov-report=html -m emergency --run-integration crypto_j_trader/tests/
) else (
    pytest -v --tb=short --strict-markers -p no:warnings --cov=crypto_j_trader --cov-report=term-missing --cov-report=xml --cov-report=html crypto_j_trader/tests/
)

:: Check exit code
if errorlevel 1 (
    echo.
    echo Test suite failed with errors
    exit /b 1
)

echo.
echo Test suite completed successfully
exit /b 0