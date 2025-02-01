#!/bin/bash

# Set the path to the project directory
PROJECT_DIR="/mnt/c/Projects/CryptoJ_Trader_New/crypto_j_trader"

# Set the path to the configuration file
CONFIG_FILE="$PROJECT_DIR/paper_config.json"

# Set the path to the main script
MAIN_SCRIPT="$PROJECT_DIR/main.py"

# Set the path to output file
OUTPUT_FILE="$PROJECT_DIR/monitor_output.txt"

while true
do
  if [ -f "$MAIN_SCRIPT" ]; then
    python3 "$MAIN_SCRIPT" --config "$CONFIG_FILE" --status > "$OUTPUT_FILE"
    echo "System status updated in $OUTPUT_FILE at $(date)"
  else
    echo "Error: Main script not found at $MAIN_SCRIPT"
  fi
  sleep 300
done