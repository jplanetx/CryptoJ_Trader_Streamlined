#!/bin/bash
# Launch script for paper trading with transition monitoring

# Configuration
CONFIG_FILE="crypto_j_trader/paper_config.json"
LOG_FILE="paper_trading.log"
METRICS_DIR="data/metrics"

# Create required directories
mkdir -p "$METRICS_DIR"
mkdir -p "data/trades"

# Start with clean log
echo "Starting paper trading transition $(date)" > "$LOG_FILE"

# Launch python process with transition monitoring
python -m crypto_j_trader.src.main \
    --config "$CONFIG_FILE" \
    --paper-trading \
    --transition-monitor \
    --metrics-dir "$METRICS_DIR" \
    --log-file "$LOG_FILE" \
    "$@"
