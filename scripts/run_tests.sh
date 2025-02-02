#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}Starting test suite execution...${NC}"

# Run unit tests
echo -e "\n${BLUE}Running unit tests...${NC}"
pytest crypto_j_trader/tests/unit -v
UNIT_RESULT=$?

# Run integration tests
echo -e "\n${BLUE}Running integration tests...${NC}"
pytest crypto_j_trader/tests/integration -v
INTEGRATION_RESULT=$?

# Generate coverage report
echo -e "\n${BLUE}Generating coverage report...${NC}"
pytest --cov=crypto_j_trader --cov-report=html
COVERAGE_RESULT=$?

# Print summary
echo -e "\n${BLUE}Test Execution Summary:${NC}"
if [ $UNIT_RESULT -eq 0 ]; then
    echo -e "${GREEN}✓ Unit tests passed${NC}"
else
    echo -e "${RED}✗ Unit tests failed${NC}"
fi

if [ $INTEGRATION_RESULT -eq 0 ]; then
    echo -e "${GREEN}✓ Integration tests passed${NC}"
else
    echo -e "${RED}✗ Integration tests failed${NC}"
fi

if [ $COVERAGE_RESULT -eq 0 ]; then
    echo -e "${GREEN}✓ Coverage report generated${NC}"
    echo -e "${BLUE}Coverage report available at: ./coverage_html_report/index.html${NC}"
else
    echo -e "${RED}✗ Coverage report generation failed${NC}"
fi

# Exit with error if any test suite failed
if [ $UNIT_RESULT -ne 0 ] || [ $INTEGRATION_RESULT -ne 0 ] || [ $COVERAGE_RESULT -ne 0 ]; then
    exit 1
fi