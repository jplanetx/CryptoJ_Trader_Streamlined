# PowerShell script for Windows users

# Colors for output
$Green = @{ForegroundColor = 'Green'}
$Red = @{ForegroundColor = 'Red'}
$Blue = @{ForegroundColor = 'Blue'}

Write-Host "Starting test suite execution..." @Blue

# Run unit tests
Write-Host "`nRunning unit tests..." @Blue
pytest crypto_j_trader/tests/unit -v
$unitResult = $LASTEXITCODE

# Run integration tests
Write-Host "`nRunning integration tests..." @Blue
pytest crypto_j_trader/tests/integration -v
$integrationResult = $LASTEXITCODE

# Generate coverage report
Write-Host "`nGenerating coverage report..." @Blue
pytest --cov=crypto_j_trader --cov-report=html
$coverageResult = $LASTEXITCODE

# Print summary
Write-Host "`nTest Execution Summary:" @Blue
if ($unitResult -eq 0) {
    Write-Host "✓ Unit tests passed" @Green
} else {
    Write-Host "✗ Unit tests failed" @Red
}

if ($integrationResult -eq 0) {
    Write-Host "✓ Integration tests passed" @Green
} else {
    Write-Host "✗ Integration tests failed" @Red
}

if ($coverageResult -eq 0) {
    Write-Host "✓ Coverage report generated" @Green
    Write-Host "Coverage report available at: ./coverage_html_report/index.html" @Blue
} else {
    Write-Host "✗ Coverage report generation failed" @Red
}

# Exit with error if any test suite failed
if ($unitResult -ne 0 -or $integrationResult -ne 0 -or $coverageResult -ne 0) {
    exit 1
}