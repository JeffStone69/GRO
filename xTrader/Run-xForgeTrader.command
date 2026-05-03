#!/bin/bash
cd "$(dirname "$0")"

echo "Starting xForgeTrader..."
source venv/bin/activate
python3 xforge_trader.py
