# Run Tests PowerShell Script

# Parameters
param(
    [string]$TestType = "all",  # Options: all, unit, integration, specific
    [string]$TestPath = "",     # Specific test path if TestType is "specific"
    [switch]$Coverage = $false, # Generate coverage report
    [switch]$Verbose = $false   # Verbose output
)

# Set error action preference
$ErrorActionPreference = "Stop"

# Function to check if virtual environment exists
function Test-VirtualEnv {
    if (!(Test-Path ".\venv")) {
        Write-Host "Creating virtual environment..."
        python -m venv venv
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to create virtual environment"
        }
    }
}

# Function to activate virtual environment
function Activate-VirtualEnv {
    Write-Host "Activating virtual environment..."
    .\venv\Scripts\Activate
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to activate virtual environment"
    }
}

# Function to install dependencies
function Install-Dependencies {
    Write-Host "Installing dependencies..."
    pip install pytest pytest-asyncio pytest-cov
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install dependencies"
    }
}

# Function to run tests
function Run-Tests {
    $testCommand = "pytest"
    if ($Verbose) {
        $testCommand += " -v"
    }

    switch ($TestType) {
        "unit" {
            $testCommand += " tests/unit/"
        }
        "integration" {
            $testCommand += " tests/integration/"
        }
        "specific" {
            if ($TestPath -eq "") {
                throw "Test path must be specified for specific test"
            }
            $testCommand += " $TestPath"
        }
        default {
            $testCommand += " tests/"
        }
    }

    if ($Coverage) {
        $testCommand += " --cov=src --cov-report=html"
    }

    Write-Host "Running tests: $testCommand"
    Invoke-Expression $testCommand
}

# Main execution
try {
    # Set location to script directory
    Set-Location $PSScriptRoot

    # Setup environment
    Test-VirtualEnv
    Activate-VirtualEnv
    Install-Dependencies

    # Run tests
    Run-Tests

    # Check results
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Tests completed successfully!" -ForegroundColor Green
        if ($Coverage) {
            Write-Host "Coverage report generated in htmlcov directory" -ForegroundColor Green
        }
    } else {
        Write-Host "Tests failed with exit code $LASTEXITCODE" -ForegroundColor Red
    }
}
catch {
    Write-Host "Error: $_" -ForegroundColor Red
    exit 1
}
finally {
    # Deactivate virtual environment if active
    if ($env:VIRTUAL_ENV) {
        deactivate
    }
}
