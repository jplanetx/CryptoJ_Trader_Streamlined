#!/bin/bash

# Set the path to the project directory
PROJECT_DIR="/mnt/c/Projects/CryptoJ_Trader_New/crypto_j_trader"

# Set the path to the configuration file
CONFIG_FILE="$PROJECT_DIR/paper_config.json"

# Set the path to the main script
MAIN_SCRIPT="$PROJECT_DIR/main.py"

# Activate the virtual environment if needed
# source "$PROJECT_DIR/venv/bin/activate"

# Launch the trading bot

if [ -f "$MAIN_SCRIPT" ]; then
  python3 "$MAIN_SCRIPT" --config "$CONFIG_FILE" &
  echo "Trading bot launched in background"
else
  echo "Error: Main script not found at $MAIN_SCRIPT"
fi
