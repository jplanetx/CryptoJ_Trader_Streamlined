#!/bin/bash
# Monitor script for paper trading transition

# Configuration
METRICS_DIR="data/metrics"
LOG_FILE="paper_trading.log"
CHECK_INTERVAL=60  # seconds

# Function to check component health
check_health() {
    local errors=0
    local warnings=0
    
    # Check trading bot status
    if ! python -m crypto_j_trader.src.tools.check_health; then
        ((errors++))
    fi
    
    # Check metrics
    if [ -f "$METRICS_DIR/health_metrics.json" ]; then
        # Count errors and warnings from metrics
        local metrics_errors=$(jq '.error_count' "$METRICS_DIR/health_metrics.json")
        local metrics_warnings=$(jq '.warning_count' "$METRICS_DIR/health_metrics.json")
        ((errors+=metrics_errors))
        ((warnings+=metrics_warnings))
    fi
    
    # Report status
    echo "$(date): Health check - Errors: $errors, Warnings: $warnings"
    
    return $errors
}

# Main monitoring loop
echo "Starting monitoring at $(date)"
while true; do
    check_health
    sleep $CHECK_INTERVAL
done