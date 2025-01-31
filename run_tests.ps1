# Run tests with proper error handling
$ErrorActionPreference = "Stop"

Write-Host "Installing package in development mode..." -ForegroundColor Green
python -m pip install -e .
if ($LASTEXITCODE -ne 0) { 
    Write-Host "Failed to install package" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "`nRunning tests..." -ForegroundColor Green
python -m pytest crypto_j_trader/tests/unit/test_basic.py -v --color=yes
if ($LASTEXITCODE -ne 0) { 
    Write-Host "Tests failed" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "`nTests completed successfully!" -ForegroundColor Green