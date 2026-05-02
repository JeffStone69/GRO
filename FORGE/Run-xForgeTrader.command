#!/bin/bash
cd "$(dirname "$0")"

echo "========================================"
echo "   xForgeTrader v7 – One-Click Launcher"
echo "========================================"
echo "Working folder: $(pwd)"

# Activate venv
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✅ venv activated"
else
    echo "❌ venv not found. Run this first in Terminal:"
    echo "python -m venv venv && source venv/bin/activate && pip install gradio yfinance pandas numpy plotly pandas-ta openai"
    read -p "Press Enter to close..."
    exit 1
fi

# Launch the script
if [ -f "xforge_trader_v7.py" ]; then
    python xforge_trader_v7.py
elif [ -f "xforge_trader.py" ]; then
    python xforge_trader.py
else
    echo "❌ No Python script found (xforge_trader_v7.py or xforge_trader.py)"
    read -p "Press Enter to close..."
    exit 1
fi
